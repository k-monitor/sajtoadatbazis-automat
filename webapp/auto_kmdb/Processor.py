from time import sleep


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
        while True:
            try:
                self.process_next()
            except Exception as e:
                print(e)
                sleep(60)
            sleep(1)
