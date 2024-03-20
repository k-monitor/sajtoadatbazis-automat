from time import sleep
from auto_kmdb.DownloadProcessor import DownloadProcessor
from auto_kmdb.ClassificationProcessor import ClassificationProcessor
from auto_kmdb.NERProcessor import NERProcessor


processors = [DownloadProcessor(), ClassificationProcessor(), NERProcessor()]


def article_processor(appcontext):
    appcontext.push()

    while True:
        print("Starting")
        if not all([p.is_done() for p in processors]):
            continue
        print('All done')
        for processor in processors:
            processor.process_next()
        sleep(1*60)
