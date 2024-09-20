from auto_kmdb.Processor import Processor
from time import sleep
from auto_kmdb.db import connection_pool, get_keyword_queue, save_keyword_step
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
        with connection_pool.get_connection() as connection:
            next_row = get_keyword_queue(connection)
        if next_row is None:
            sleep(30)
            return
        logging.info("keyword processor next")
        self.predict()

        # TODO

        with connection_pool.get_connection() as connection:
            save_keyword_step(connection, next_row["id"])
