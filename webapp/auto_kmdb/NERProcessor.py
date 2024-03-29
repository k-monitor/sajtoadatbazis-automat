from transformers import pipeline, AutoTokenizer
from auto_kmdb.db import get_ner_queue, add_auto_person, add_auto_institution
from auto_kmdb.db import add_auto_place, get_all_persons, get_all_institutions
from auto_kmdb.db import save_ner_step, get_all_places
from auto_kmdb.Processor import Processor
from time import sleep
from auto_kmdb.db import connection_pool


class NERProcessor(Processor):
    def __init__(self):
        #super().__init__()
        self.done = False

    def load_model(self):
        self.classifier = pipeline("ner", model="boapps/kmdb_ner_model",
                                   aggregation_strategy="average",
                                   tokenizer=AutoTokenizer.from_pretrained("boapps/kmdb_ner_model", model_max_length=512))
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
            print(entity)
            label, e_type = entity['entity_group'].split('_')
            found_name = self.text[entity['start']:entity['end']]
            entity_object = {
                    'classification_label': 1 if label == 'POS' else 0,
                    'classification_score': float(entity['score']),
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

    def get_person(self, person):
        all_people = get_all_persons(self.connection)
        names_in = [p for p in all_people if p['name'] and p['name'] in person['name']]
        in_names = [p for p in all_people if p['name'] and person['name'] in p['name']]
        same_names = [p for p in all_people if p['name'] and p['name'] == person['name']]
        print('process persons')
        print(person['name'])
        print(len(same_names))
        print(len(in_names))
        print(len(names_in))
        if len(same_names) == 1:
            return same_names[0]
        if len(in_names) == 1:
            return in_names[0]
        if len(names_in) == 1:
            return names_in[0]
        return None

    def get_institution(self, institution):
        all_institutions = get_all_institutions(self.connection)
        names_in = [p for p in all_institutions if p['name'] and p['name'] in institution['name']]
        in_names = [p for p in all_institutions if p['name'] and institution['name'] in p['name']]
        same_names = [p for p in all_institutions if p['name'] and p['name'] == institution['name']]
        if len(same_names) == 1:
            return same_names[0]
        if len(in_names) == 1:
            return in_names[0]
        if len(names_in) == 1:
            return names_in[0]
        return None

    def get_place(self, place):
        all_places = get_all_places(self.connection)
        names_in = [p for p in all_places if p['name'] and p['name'] in place['name']]
        in_names = [p for p in all_places if p['name'] and place['name'] in p['name']]
        same_names = [p for p in all_places if p['name'] and p['name'] == place['name']]
        if len(same_names) == 1:
            return same_names[0]
        if len(in_names) == 1:
            return in_names[0]
        if len(names_in) == 1:
            return names_in[0]
        return None

    def process_next(self):
        self.connection = connection_pool.get_connection()
        next_row = get_ner_queue(self.connection)
        if next_row is None:
            self.connection.close()
            sleep(30)
            return

        self.text = next_row['text']
        self.predict()

        added_persons = []
        added_institutions = []
        added_places = []

        for person in self.people:
            if ' ' not in person['name']:
                continue
            for added_person in added_persons:
                if person['name'] in added_person:
                    break
            else:
                person_db = self.get_person(person)
                pid = person_db['id'] if person_db else None
                pname = person_db['name'] if person_db else None
                if pname is not None:
                    added_persons.append(pname)
                add_auto_person(self.connection, next_row['id'], pname, pid, person['found_name'],
                                person['found_position'], person['name'],
                                person['classification_score'],
                                person['classification_label'])

        for institution in self.institutions:
            institution_db = self.get_institution(institution)
            iid = institution_db['id'] if institution_db else None
            iname = institution_db['name'] if institution_db else None
            if iname is not None:
                added_institutions.append(iname)
            add_auto_institution(self.connection, next_row['id'], iname, iid, institution['found_name'],
                                 institution['found_position'], institution['name'],
                                 institution['classification_score'],
                                 institution['classification_label'])

        for place in self.places:
            place_db = self.get_place(place)
            plid = place_db['id'] if place_db else None
            plname = place_db['name'] if place_db else None
            if plname is not None:
                added_places.append(plname)
            add_auto_place(self.connection, next_row['id'], plname, plid, place['found_name'],
                           place['found_position'], place['name'],
                           place['classification_score'],
                           place['classification_label'])

        save_ner_step(self.connection, next_row['id'])
        self.connection.close()
