from time import sleep
import DownloadProcessor
import ClassificationProcessor
import NERProcessor


processors = [DownloadProcessor(), ClassificationProcessor(), NERProcessor()]


def article_processor(appcontext):
    appcontext.push()

    while True:
        if not all([p.is_done() for p in processors]):
            continue
        for processor in processors:
            processor.process_next()
        sleep(1*60)
