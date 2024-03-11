from transformers import pipeline
from auto_kmdb.db import get_ner_queue, add_auto_person, add_auto_institution
from auto_kmdb.db import add_auto_place, get_all_persons, get_all_institutions, get_all_places
from auto_kmdb.Processor import Processor
from time import sleep


class NERProcessor(Processor):
    def __init__(self):
        self.done = False

    def load_model(self):
        self.classifier = pipeline("ner", model="boapps/kmdb_ner_model", aggregation_strategy="average")
        self.done = True
        print("NER model loaded")

    def is_done(self):
        return self.done

    def predict(self):
        self.people = []
        self.institutions = []
        self.places = []
        self.classifications = self.classifier(self.text)
        for entity in self.classifications:
            label, e_type = entity['entity_group'].split('-')
            found_name = self.text[entity['start']:entity['end']]
            entity_object = {
                    'classification_label': label,
                    'classification_score': entity['score'],
                    'found_name': found_name,
                    'name': found_name,
                    'found_position': entity['start'],
                }
            if e_type == 'PER':
                self.people.append(entity_object)
            elif e_type == 'ORG':
                self.institutions.append(entity_object)
            elif e_type == 'LOC':
                self.places.append(entity_object)

            # TODO: add_auto_person(autokmdb_news_id, person_id, found_name, found_position, name, classification_score, classification_label)

    def get_person_id(self, person):
        all_people = get_all_persons()
        names_in = [p for p in all_people if p['name'] in person['name']]
        in_names = [p for p in all_people if person['name'] in p['name']]
        same_names = [p for p in all_people if p['name'] == person['name']]
        if len(same_names) == 1:
            return same_names[0]['id']
        if len(in_names) == 1:
            return names_in[0]['id']
        if len(names_in) == 1:
            return names_in[0]['id']
        return None

    def get_institution_id(self, institution):
        all_institutions = get_all_institutions()
        names_in = [p for p in all_institutions if p['name'] in institution['name']]
        in_names = [p for p in all_institutions if institution['name'] in p['name']]
        same_names = [p for p in all_institutions if p['name'] == institution['name']]
        if len(same_names) == 1:
            return same_names[0]['id']
        if len(in_names) == 1:
            return names_in[0]['id']
        if len(names_in) == 1:
            return names_in[0]['id']
        return None

    def get_place_id(self, place):
        all_places = get_all_places()
        names_in = [p for p in all_places if p['name'] in place['name']]
        in_names = [p for p in all_places if place['name'] in p['name']]
        same_names = [p for p in all_places if p['name'] == place['name']]
        if len(same_names) == 1:
            return same_names[0]['id']
        if len(in_names) == 1:
            return names_in[0]['id']
        if len(names_in) == 1:
            return names_in[0]['id']
        return None

    def process_next(self):
        next_row = get_ner_queue()
        if next_row is None:
            sleep(30)

        self.text = next_row['text']
        self.predict()

        for person in self.people:
            person_id = self.get_person_id(person)
            add_auto_person(next_row['id'], person_id, person['found_name'],
                            person['found_position'], person['name'],
                            person['classification_score'],
                            person['classification_label'])

        for institution in self.institutions:
            institution_id = self.get_institution_id(institution)
            add_auto_institution(next_row['id'], institution_id, institution['found_name'],
                                 institution['found_position'], institution['name'],
                                 institution['classification_score'],
                                 institution['classification_label'])

        for place in self.places:
            place_id = self.get_place_id(place)
            add_auto_place(next_row['id'], place_id, place['found_name'],
                           place['found_position'], place['name'],
                           place['classification_score'],
                           place['classification_label'])

        self.predict()
