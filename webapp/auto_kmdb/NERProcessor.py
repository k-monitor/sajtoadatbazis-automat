from transformers import pipeline, AutoTokenizer
from auto_kmdb.db import get_ner_queue, add_auto_person, add_auto_institution
from auto_kmdb.db import add_auto_place, get_all_persons, get_all_institutions
from auto_kmdb.db import save_ner_step, get_all_places
from auto_kmdb.entity_linking import (
    get_entities_freq,
    get_mapping,
    comb_mappings,
    get_synonyms_file,
)
from auto_kmdb.Processor import Processor
from time import sleep
from auto_kmdb.db import connection_pool
import pandas as pd
import logging
import torch
from typing import Literal


def join_entities(classifications: list[dir]):
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
    new_classifications = []
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


def strip_entity(entity):
    entity["word"] = entity["word"].strip("-")
    return entity


class NERProcessor(Processor):
    def __init__(self):
        # super().__init__()
        logging.info("initialized ner processor")
        self.done = False

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
        )

        self.done = True
        logging.info("ner processor loaded model")

    def is_done(self):
        return self.done

    def predict(self):
        logging.info("ner processor is running prediction")
        self.people = []
        self.institutions = []
        self.places = []
        self.classifications = [
            strip_entity(e)
            for e in join_entities(self.classifier(self.text))
            if len(e["word"]) > 3
        ]
        for entity in self.classifications:
            logging.info(entity)
            label, e_type = entity["entity_group"].split("_")
            found_name = self.text[entity["start"] : entity["end"]]
            entity_object = {
                "classification_label": 1 if label == "POS" else 0,
                "classification_score": float(entity["score"]),
                "found_name": found_name,
                "name": found_name,
                "found_position": entity["start"],
            }
            if e_type == "PER":
                self.people.append(entity_object)
            elif e_type == "ORG":
                self.institutions.append(entity_object)
            elif e_type == "LOC":
                self.places.append(entity_object)

            # TODO: add_auto_person(autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label)

    def get_db_entity_linking(
        self,
        detected_entities: list[dir],
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
        logging.info(entity_type)
        logging.info(detected_entities)
        synonym_mapping = (
            get_synonyms_file(entity_type)
            if (entity_type in ["places", "institutions"])
            else None
        )
        keywords = get_entities_freq(entity_type)
        mapping = get_mapping(detected_entities, keywords.index, synonym_mapping)
        combed_mapping = comb_mappings(mapping, keywords)

        # drop single-word person suggestions if we failed to map them to db
        if entity_type == "people":
            combed_mapping = combed_mapping.loc[
                [(len(x.split(" ")) > 1) for x in combed_mapping.detected_ent]
                | combed_mapping.combed_mapping.notna()
            ]
        return combed_mapping

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_row = get_ner_queue(connection)
        if next_row is None:
            sleep(30)
            return
        torch.cuda.empty_cache()

        self.text = next_row["text"]
        self.predict()

        print("ner processing: " + str(next_row["id"]))
        logging.info("ner processing next: " + str(next_row["id"]))

        for type, detected_entities, db_function in [
            ("people", self.people, add_auto_person),
            ("places", self.places, add_auto_place),
            ("institutions", self.institutions, add_auto_institution),
        ]:
            if len(detected_entities) > 0:
                mapping = self.get_db_entity_linking(detected_entities, type)
                logging.info(mapping)
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
                            entity_infos.loc["detected_ent"],
                            str(entity_infos.loc["score"]),
                            str(entity_infos.loc["class"]),
                        )

        with connection_pool.get_connection() as connection:
            save_ner_step(connection, next_row["id"])
