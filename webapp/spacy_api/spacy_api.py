from fastapi import FastAPI
from pydantic import BaseModel
import spacy


class Data(BaseModel):
    text: str


nlp = spacy.load("hu_core_news_trf")
app = FastAPI()


@app.post("/text/")
def extract_entities(data: Data):
    doc = nlp(data.text)
    ents = []
    for ent in doc.ents:
        ents.append({"text": ent.text, "label_": ent.label_})
    return {"message": data.text, "lang": "TODO", "ents": ents}


def distinct(entity_list):
    distinct_entity_list = []
    for entity in entity_list:
        for entity2 in entity_list:
            if len(entity) < len(entity2) and entity in entity2:
                break
        else:
            distinct_entity_list.append(entity)
    return list(set(distinct_entity_list))


@app.post("/entities")
def entities(data: Data):
    doc = nlp(data.text)
    people = [entity.lemma_ for entity in doc.ents if entity.label_ == "PER"]
    institutions = [entity.lemma_ for entity in doc.ents if entity.label_ == "ORG"] 
    distinct_people = distinct(people)
    distinct_institutions = distinct(institutions)

    return {
        "people": ', '.join(distinct_people),
        "institutions": ', '.join(distinct_institutions)
        }
