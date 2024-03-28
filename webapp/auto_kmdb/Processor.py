from time import sleep
from auto_kmdb.db import connection_pool


class Processor:
    def __init__(self):
        self.connection = connection_pool.get_connection()

    def load_model(self):
        pass

    def predict(self):
        pass

    def process_next(self):
        pass

    def is_done(self):
        return True

    def process_loop(self):
        while True:
            try:
                self.process_next()
            except Exception as e:
                print(e)
                sleep(60)
            sleep(1)
