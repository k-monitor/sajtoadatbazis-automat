from auto_kmdb.Processor import Processor
from time import sleep
from auto_kmdb.db import connection_pool, get_keyword_queue, save_keyword_step


class KeywordProcessor(Processor):
    def __init__(self):
        #super().__init__()
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
        self.connection = connection_pool.get_connection()
        next_row = get_keyword_queue(self.connection)
        if next_row is None:
            self.connection.close()
            sleep(30)
            return
        self.predict()

        # TODO

        save_keyword_step(self.connection, next_row['id'])
        self.connection.close()
