from time import sleep
import logging


class Processor:
    def __init__(self):
        pass

    def load_model(self):
        pass

    def predict(self):
        pass

    def process_next(self):
        pass

    def is_done(self):
        return True

    def process_loop(self):
        logging.info('started process_loop')
        while True:
            try:
                self.process_next()
            except Exception as e:
                logging.error('encountered error in processing loop')
                logging.error(e)
                sleep(60)
            sleep(1)
