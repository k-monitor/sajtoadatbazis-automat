from os import environ
from transformers import pipeline, AutoTokenizer, Pipeline
from auto_kmdb.db import get_ner_queue, add_auto_person, add_auto_institution
from auto_kmdb.db import add_auto_place, get_all_persons, get_all_institutions
from auto_kmdb.db import save_ner_step, get_all_places, skip_processing_error
from auto_kmdb.utils.entity_linking import (
    get_entities_freq,
    get_mapping,
    comb_mappings,
    get_synonyms_file,
)
from auto_kmdb.processors import Processor
from time import sleep
from auto_kmdb.db import connection_pool
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import pandas as pd
import logging
import torch
from typing import Literal, Optional
import traceback
import gc
import spacy
from spacy.language import Language


def join_entities(classifications: list[dict]) -> list[dict]:
    """
    Joins detected entities if entity_i and entity_i+1 are beside eachother in the text. This is
    necessary as BERT sometimes mistakenly splits some entities e.g. in case of detached ending:
    "Budapest" "-en").

    Args:
        classifications: list of dirs, each dir must contain the following infos of detected
        entity: word (string) e.g. 'Budapest', start(int) e.g. 10, end(int) e.g. 18 , score(float)
        e.g. 0.998, entity_group(str) e.g. 'POS-LOC'

    Returns:
        list of dirs, where the infos of the neighbouring entities have been merged:
            - word: concatenated
            - start: taken from the first entity
            - end: taken from the last entity
            - score: mean of the score of the two entities
            - entity_group: classification is POS if any of the entities is POS, entity type is
            taken from the first entity
    """
    new_classifications: list[dict] = []
    last_end = -1
    for classification in classifications:
        if classification["start"] == last_end:
            new_classifications[-1]["word"] += classification["word"]
            new_classifications[-1]["end"] = classification["end"]
            new_classifications[-1]["score"] = (
                new_classifications[-1]["score"] + classification["score"]
            ) / 2
            new_classifications[-1]["entity_group"] = (
                new_classifications[-1]["entity_group"].split("-")[0]
                + "-"
                + (
                    "POS"
                    if ("POS" in new_classifications[-1]["entity_group"])
                    | ("POS" in classification["entity_group"])
                    else "NEG"
                )
            )
        else:
            new_classifications.append(classification)
        last_end = classification["end"]
    return new_classifications


def strip_entity(entity: dict):
    entity["word"] = entity["word"].strip("-")
    return entity


class NERProcessor(Processor):
    def __init__(self):
        # super().__init__()
        logging.info("initialized ner processor")
        self.done: bool = False
        self.classifier: Pipeline
        self.nlp: Language

    def load_model(self):
        logging.info("ner processor is loading model")
        self.classifier = pipeline(
            "ner",
            model="boapps/kmdb_ner_model",
            aggregation_strategy="first",
            stride=8,
            tokenizer=AutoTokenizer.from_pretrained(
                "SZTAKI-HLT/hubert-base-cc", model_max_length=512
            ),
            device=environ.get("DEVICE", "cpu"),
        )
        self.nlp = spacy.load(
            "hu_core_news_lg",
            disable=[
                "parser",
                "ner",
                "lookup_lemmatizer",
                "tagger",
                "senter",
            ],
        )

        self.done = True
        logging.info("ner processor loaded model")

    def is_done(self):
        return self.done

    def predict(self, text) -> tuple[list[dict], list[dict], list[dict]]:
        logging.info("ner processor is running prediction")
        people: list[dict] = []
        institutions: list[dict] = []
        places: list[dict] = []
        classifications: list[dict] = [
            strip_entity(e)
            for e in join_entities(self.classifier(text))
            if len(e["word"]) > 3
        ]
        for entity in classifications:
            logging.info(entity)
            label, e_type = entity["entity_group"].split("_")
            found_name = text[entity["start"] : entity["end"]]
            entity_object = {
                "classification_label": 1 if label == "POS" else 0,
                "classification_score": float(entity["score"]),
                "found_name": found_name,
                "name": found_name,
                "found_position": entity["start"],
            }
            if e_type == "PER":
                people.append(entity_object)
            elif e_type == "ORG":
                institutions.append(entity_object)
            elif e_type == "LOC":
                places.append(entity_object)

            # TODO: add_auto_person(autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label)
        return people, institutions, places

    def get_db_entity_linking(
        self,
        detected_entities: list[dict],
        entity_type: Literal["people", "places", "institutions"],
    ) -> pd.DataFrame:
        """
        Given the set of detected entities, it returns tha mapped db keywords.

        Args:
            detected_entities: list of dirs, each dir must contain the following infos of a detected
                entity: word (string) e.g. 'Budapest', score(float) e.g. 0.998, entity_group(str) e.g.
                'POS-LOC'
            entity_type: the type of entities we want to link to db, value must be either set to 'people',
                'places' or 'institutions'

        Returns:
            Dataframe containing the mappings, indexed by the found entities' start charachter.
            Contains the following infos:

            'class': 1 if positive, 0 if negative. It takes value of 1 if any of the detected
                entities linked to this db keyword has been classified as positive
            'score': classification score, takes the highest score from the score of the detected
                entities linked to this db keyword that have the same class
            'start': position of the first character of the detected entity that the 'score'
                belongs to
            'detected_ent_raw': the detected entity in the form it appears in text
            'detected_ent': the detected entity after stemming
            'combed_mapping': suggested db keyword mapping
            'keyword_id': the id of the suggested db keyword mapping
        """
        # logging.info(entity_type)
        # logging.info(detected_entities)
        synonym_mapping: Optional[pd.DataFrame] = (
            get_synonyms_file(entity_type)
            if (entity_type in ["places", "institutions"])
            else None
        )
        if synonym_mapping is not None:
            lowercase_mapping: Optional[pd.DataFrame] = synonym_mapping.copy()
            lowercase_mapping.index = lowercase_mapping.index.str.lower()
        else:
            lowercase_mapping = None
        keywords: pd.DataFrame = get_entities_freq(entity_type)
        mapping: pd.DataFrame = get_mapping(
            detected_entities, keywords.index, self.nlp, lowercase_mapping
        )
        combed_mapping: pd.DataFrame = comb_mappings(mapping, keywords)

        # drop single-word person suggestions if we failed to map them to db
        if entity_type == "people":
            combed_mapping = combed_mapping.loc[
                [(len(x.split(" ")) > 1) for x in combed_mapping.detected_ent]
                | combed_mapping.combed_mapping.notna()
            ]

        del mapping
        del keywords
        del synonym_mapping
        del lowercase_mapping
        gc.collect()

        return combed_mapping

    def do_process(self, next_row):
        def add_institution_dot(name, ent_type):
            if (
                name.endswith("Kft")
                or name.endswith("Zrt")
                or name.endswith("Kht")
                or name.endswith("Nyrt")
                or name.endswith("Bt")
            ) and ent_type == "institutions":
                return name + "."
            return name

        text: str = next_row["text"]
        people, institutions, places = self.predict(text)

        print("ner processing: " + str(next_row["id"]))
        logging.info("ner processing next: " + str(next_row["id"]))

        for type, detected_entities, db_function in [
            ("people", people, add_auto_person),
            ("places", places, add_auto_place),
            ("institutions", institutions, add_auto_institution),
        ]:
            if len(detected_entities) > 0:
                mapping: pd.DataFrame = self.get_db_entity_linking(
                    detected_entities, type
                )
                # logging.info(mapping)
                assert mapping.index.is_unique, (
                    "Database " + type + " keywords to be added should be unique"
                )
                for start_char in mapping.index.values:
                    entity_infos = mapping.loc[start_char]
                    with connection_pool.get_connection() as connection:
                        db_function(
                            connection,
                            next_row["id"],
                            entity_infos.loc["combed_mapping"],
                            str(entity_infos.loc["keyword_id"]),
                            entity_infos.loc["detected_ent_raw"],
                            str(start_char),
                            add_institution_dot(entity_infos.loc["detected_ent"], type),
                            str(entity_infos.loc["score"]),
                            str(entity_infos.loc["class"]),
                        )
                del mapping
                gc.collect()

        with connection_pool.get_connection() as connection:
            save_ner_step(connection, next_row["id"])

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_rows: list = get_ner_queue(connection)
        for next_row in next_rows:
            if next_row is None:
                sleep(10)
                return
            torch.cuda.empty_cache()
            try:
                self.do_process(next_row)
            except Exception as e:
                skip_processing_error(connection, next_row["id"])
                logging.warn("exception during: " + str(next_row["id"]))
                logging.error(e)
                print(traceback.format_exc())
                logging.error(traceback.format_exc())
