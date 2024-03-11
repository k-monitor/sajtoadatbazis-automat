from time import sleep

class Processor:
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
            self.process_next()
            sleep(1)
