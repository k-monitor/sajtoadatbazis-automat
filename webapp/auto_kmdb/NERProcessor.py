from transformers import pipeline
from db import get_ner_queue, add_auto_person, add_auto_institution, add_auto_place
from time import sleep


class Processor:
    def load_model(self):
        self.classifier = pipeline("ner", model="boapps/kmdb_ner_model", aggregation_strategy="average")

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

    def process_next(self):
        next_row = get_ner_queue()
        if next_row is None:
            sleep(30)

        for person in self.people:
            add_auto_person(next_row['id'], person_id, person['found_name'],
                            person['found_position'], person['name'],
                            person['classification_score'],
                            person['classification_label'])
        for institution in self.institutions:
            add_auto_institution(next_row['id'], institution_id, institution['found_name'],
                                 institution['found_position'], institution['name'],
                                 institution['classification_score'],
                                 institution['classification_label'])
        for place in self.places:
            add_auto_place(next_row['id'], place_id, place['found_name'],
                           place['found_position'], place['name'],
                           place['classification_score'],
                           place['classification_label'])

        self.predict()
