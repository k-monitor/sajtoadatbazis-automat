from auto_kmdb.processors import Processor
from time import sleep
from auto_kmdb import db
import logging


class KeywordProcessor(Processor):
    def __init__(self):
        # super().__init__()
        logging.info("initialized keyword processor")
        self.done = False

    def load_model(self):
        # TODO
        self.done = True

    def is_done(self):
        return self.done

    def predict(self):
        # TODO
        pass

    def process_next(self):
        with db.connection_pool.get_connection() as connection:
            next_rows: list = db.get_keyword_queue(connection)
        for next_row in next_rows:
            if next_row is None:
                sleep(30)
                return
            logging.info("keyword processor next")
            self.predict()

            # TODO

            with db.connection_pool.get_connection() as connection:
                db.save_keyword_step(connection, next_row["id"])
