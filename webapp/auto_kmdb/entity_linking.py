import pandas as pd
import numpy as np
from typing import Literal, Optional, Sequence
import spacy

pd.set_option("future.no_silent_downcasting", True)
nlp = spacy.load(
    "hu_core_news_lg",
    disable=[
        "parser",
        "ner",
        "lookup_lemmatizer",
        "tagger",
        "senter",
    ],
)

from auto_kmdb.db import connection_pool
from auto_kmdb.db import (
    get_all_persons_freq,
    get_all_institutions_freq,
    get_all_places_freq,
)


def get_synonyms_file(entity_type: Literal["places", "institutions"] = "places") -> pd.DataFrame:
    """
    Loads synonym aliases for places or institutions from csv files.

    Args:
        entity_type: must be of value "places" or "institutions" because we do not have synonym
            files for people
    
    Returns:
        Dataframe indexed by aliases and contianing a column 'db_keyword' the alias belongs to.
        Aliases must be unique.
    """
    if entity_type == "places":
        synonym_file = pd.read_csv("places_synonym.csv", index_col=[0])
    if entity_type == "institutions":
        synonym_file = (
            pd.read_csv("institutions_synonym.csv", index_col=[0])
            .drop(
                columns=[
                    "no_detections",
                    "no_db_keywords",
                    "number_of_missed_detections",
                    "címkézési szabály",
                ]
            )
            .T
        )

    synonym_mapping = pd.DataFrame(columns=["db_keyword"])
    synonym_mapping.index.name = "entity"

    for col in synonym_file.columns:
        synonyms = synonym_file[col].dropna().values
        for word in synonyms:
            synonym_mapping.loc[word.strip()] = col.strip()
    assert synonym_mapping.index.duplicated().sum() == 0
    return synonym_mapping


def get_entities_freq(
    type: Literal["people", "places", "institutions"]
) -> pd.DataFrame:
    """
    Queries entitites from database and counts their occurrances on articles.

    Args:
        type: type of entity to query, must have value of either 'people', 'places', or
        'institutions'

    Returns:
        Dataframe indexed by db keyword names, containing 'id' and 'count' column.
    """
    with connection_pool.get_connection() as connection:
        if type == "people":
            db_entities = get_all_persons_freq(connection)
        elif type == "places":
            db_entities = get_all_places_freq(connection)
        elif type == "institutions":
            db_entities = get_all_institutions_freq(connection)
        else:
            raise ValueError(
                "type parameter should be one of the following: 'people', 'places', 'institutions'"
            )
    db_entities = (
        pd.DataFrame(db_entities)
        .convert_dtypes(
            {"name": str, "id": int, "count": int},
        )
        .drop_duplicates(
            subset="name"
        )  # TODO: remove this line after DB has been cleaned
        .dropna()  # TODO: remove this line after DB has been cleaned
    )

    for col in db_entities.columns:
        assert (~db_entities[col].isna()).all(), (
            type + " keyword " + col + " should not contain NaNs"
        )
    assert db_entities.name.is_unique, "Keyword names should be unique"
    assert np.array(
        [("," not in str(entity_name)) for entity_name in db_entities.index.values]
    ).all(), "entity names shoudl not contain commas ','"
    return db_entities.set_index("name")


def get_identical_keywords(entity: str, keyword_list: Sequence[str]) -> list[str]:
    """
    Returns a list containing the keyword from keyword_list that is identical with the given
    entity.

    Args:
        entity: the entity to be linked
        keyword_list: list of db keyword names

    Returns:
        List of the identical keyword, or empty list if there is none.
    """
    keywords = [entity] if entity in keyword_list else []
    return keywords


def get_containing_keywords(entity: str, keyword_list: Sequence[str]) -> list[str]:
    """
    Returns a list of db keywords from keyword_list that contain the given entity.

    Args:
        entity: the entity to be linked
        keyword_list: list of db keyword names

    Returns:
        List of the conrtaining keywords, or empty list if there is none.
    """
    keywords = []
    for keyword in keyword_list:
        if entity in keyword:
            keywords.append(keyword)
    return keywords


def get_mapping_from_article(entity: str, all_entities: Sequence[str]) -> list[str]:
    """
    Returns a list of entities from all_entites that contain the given entity.

    Args:
        entity: the entity to be linked
        all_entities: list of db entity names

    Returns:
        List of the conrtaining entities, or empty list if there is none.
    """
    keywords = get_containing_keywords(entity, all_entities)
    keywords.remove(entity)
    return keywords


def get_mapping_by_synonym(entity: str, synonym_mapping: pd.DataFrame) -> list[str]:
    """
    Returns a list containing the db keyword if the given entity is identical to any of the
    aliases of the keyword listed in the synonym_mapping db.

    Args:
        entity: the entity to be linked
        synonym_mapping: dataframe indexed by aliases, containing a single column named
            'db_keyword' that hold the name of the db keyword the alias belongs to.

    Returns:
        List of the db keyword, or empty list if there is none.
    """
    return (
        [synonym_mapping.loc[entity, "db_keyword"]]
        if entity in synonym_mapping.index.values
        else []
    )


def get_mapping(
    detected_entities: list[dir],
    keyword_list: Sequence[str],
    synonym_mapping: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Receives the detected entities of a single article and a list of keywords taken from the DB. If
    an entity is detected multiple times, the algorithm performs the linking only once and takes the
    'class', 'score', 'start', 'detected_ent_raw' infos of the detection with the highest class and
    score.

    The linking is a rule-based algorithm with the following rules:
        1. Linking from the article: It checks if an entity could be linked with any other entity
        from the article. E.g. 'Kiss Bandi' is also referred to as 'Kiss' in the article. In this
        case, the detections of 'Kiss' will be linked to 'Kiss Bandi', and later only
        'Kiss Bandi' will be linked to a db keyword.
        2. Linking with identical keyword: The algorithm searches for exact matches from the db
        keywords. E.g. if there is a db keyword named 'Kiss Bandi', then the entity will be linked
        to that.
        3. Linking if a db keyword contains the the entity: The algorithm searches for cases when
        the db keyword contains the given entity. E.g. the entity 'Kiss Bandi' can be linked to
        both 'Kiss Bandi (junior)' and 'Kiss Bandi (senior)' db keywords.
        4. Linking if the entity contains a db keywrod: The algorithm searches for cases when the
        entity conatins one of the db keywords. E.g. when the entity 'Kiss Bandi Feri' contains the
        db keyword 'Kiss Bandi'.
        5. Synonym based linking: The algorithm checks if there are any known aliases of db
        keywords that the entity is identical to. E.g. 'Kelenföl' is linked to 'XI. kerület'.
        This rule is optional.

    Args:
        detected entities: list of dirs, each dir must contain the following infos of a detected
            entity: word (string) e.g. 'Budapest', score(float) e.g. 0.998, entity_group(str) e.g.
            'POS-LOC'
        keyword list: list of db keyword names
        synonym_mapping: dataframe indexed by aliases, containing a single column named
            'db_keyword' that hold the name of the db keyword the alias belongs to, optional

    Returns:
        A dataframe indexed by the found entities, containing the proposed keyword mappings of the
        different mapping rules in separate columns
    """
    mapping = pd.DataFrame(
        detected_entities,
    ).rename(
        columns={
            "found_name": "detected_ent",
            "classification_label": "class",
            "classification_score": "score",
            "found_position": "start",
        }
    )

    mapping["detected_ent_raw"] = mapping["detected_ent"].copy()
    mapping["detected_ent"] = mapping["detected_ent"].apply(
        lambda word: " ".join([token.lemma_ for token in nlp(word)])
    )
    mapping["detections"] = 1
    mapping = (
        mapping.groupby("detected_ent")[["detections"]]
        .sum()
        .join(
            mapping.sort_values(by=["class", "score"], ascending=False)
            .groupby("detected_ent")
            .first()[["class", "score", "start", "detected_ent_raw"]]
        )
    )
    for entity in mapping.index:
        mapping.at[entity, "from_article"] = ", ".join(
            [x for x in get_mapping_from_article(entity, mapping.index)]
        )
        mapping.at[entity, "identical_keyword"] = ", ".join(
            [x for x in get_identical_keywords(entity, keyword_list)]
        )
        mapping.at[entity, "keyword_contains_entity"] = ", ".join(
            [x for x in get_containing_keywords(entity, keyword_list)]
        )
        entity_c_kw = []
        [
            (
                entity_c_kw.append(kw)
                if (len(get_containing_keywords(kw, [entity])) > 0) & (kw != entity)
                else ""
            )
            for kw in keyword_list
        ]
        mapping.at[entity, "entity_contains_keyword"] = ", ".join(entity_c_kw)

        mapping.at[entity, "synonym_keyword"] = (
            ", ".join([x for x in get_mapping_by_synonym(entity, synonym_mapping)])
            if synonym_mapping is not None
            else None
        )

    return mapping.replace("", np.NAN)


def comb_mappings(
    mapping: pd.DataFrame,
    keywords: pd.DataFrame,
    combine_columns: list[str] = [
        "identical_keyword",
        "keyword_contains_entity",
        "entity_contains_keyword",
        "synonym_keyword",
    ],
) -> pd.DataFrame:
    """
    Combines the mapping of the different rules. First it checks in-article mapping for all cases
    where there is no identical_keyword mapping available. Then it selects mappings from the
    'combine_columns' in a combine-first manner. If there are multiple keyword proposals, it
    priorizes the one with the highest db freqency.

    Args:
        mapping: dataframe indexed by the found entities, must contain the proposed keyword
        mappings of the different mapping rules in separate columns named according to the
        combine_columns parameter
        keywords: dataframe indexed by the name of db keywords, containing 'id' and 'count' columns
        combine_columns: the final mapping will be the result fo the combining the columns listed

    Returns:
        Dataframe containing the mappings, indexed by db keyword ids. Contains the following infos:
            'detections': number of detected entities from the article that have been linked to
            this db keyword
            'class': 1 if positive, 0 if negative. It takes value of 1 if any of the detected
            entities linked to this db keyword has been classified as positive
            'score': classification score, takes the highest score from the score of the detected
            entities linked to this db keyword that have the same class
            'start': position of the first character of the detected entity that the 'score'
            belongs to
            'detected_ent_raw': the detected entity in the form it appears in text
            'detected_ent': the detected entity after stemming
    """
    mapping = mapping.copy()

    mapped_from_article = mapping.loc[
        mapping["from_article"].notna() & mapping["identical_keyword"].isna()
    ].index

    for detected_ent in mapped_from_article:
        map_to = mapping.loc[detected_ent, "from_article"].split(", ")[-1]
        mapping.loc[map_to, "detections"] = mapping.loc[
            [map_to, detected_ent], "detections"
        ].sum()
        sorted_values = (
            mapping.loc[[map_to, detected_ent]]
            .sort_values(by=["class", "score"], ascending=False)
            .iloc[0][["score", "class", "start", "detected_ent_raw"]]
        )
        mapping.loc[map_to, "score"] = sorted_values["score"]
        mapping.loc[map_to, "class"] = sorted_values["class"]
        mapping.loc[map_to, "start"] = sorted_values["start"]
        # mapping.loc[map_to, 'detected_ent_raw'] = sorted_values["detected_ent_raw"]

    mapping = mapping.loc[~mapping.index.isin(mapped_from_article)]

    mapping["combed_mapping"] = np.NaN
    for col in combine_columns:
        mapping["combed_mapping"] = mapping["combed_mapping"].combine_first(
            mapping[col]
        )
    mapping["combed_mapping"] = (
        mapping["combed_mapping"]
        .apply(
            lambda x: (
                str(x).split(", ")[0]
                if len(str(x).split(", ")) == 1
                else keywords.loc[str(x).split(", "), "count"].index[-1]
            )
        )
        .replace("nan", np.NaN)
        .replace("None", np.NaN)
    )

    mapping.loc[mapping["combed_mapping"].notna(), "keyword_id"] = keywords.loc[
        mapping.loc[mapping["combed_mapping"].notna(), "combed_mapping"], "id"
    ].values

    mapping = (
        mapping.reset_index()
        .groupby("keyword_id")[["detections"]]
        .sum()
        .join(
            mapping.reset_index()
            .sort_values(by=["class", "score"], ascending=False)
            .groupby("keyword_id")
            .first()[
                [
                    "combed_mapping",
                    "class",
                    "score",
                    "start",
                    "detected_ent",
                    "detected_ent_raw",
                ]
            ]
        )
    )

    return mapping
