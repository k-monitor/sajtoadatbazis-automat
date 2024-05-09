from flask import Flask
from threading import Thread
import os
from time import sleep
sleep(10) # TODO better wait handling
from auto_kmdb.DownloadProcessor import DownloadProcessor
from auto_kmdb.ClassificationProcessor import ClassificationProcessor
from auto_kmdb.NERProcessor import NERProcessor
from auto_kmdb.KeywordProcessor import KeywordProcessor
from auto_kmdb.rss_watcher import rss_watcher


def create_app():
    app = Flask(__name__, instance_relative_config=True, )

    with app.app_context():
        from auto_kmdb.routes import api
        app.register_blueprint(api)

    #Thread(target=rss_watcher, args=(app.app_context(),), daemon=True).start()

    processors = [DownloadProcessor(), ClassificationProcessor(), NERProcessor(), KeywordProcessor()]
    for processor in processors:
        processor.load_model()
        Thread(target=processor.process_loop, args=(), daemon=True).start()


    @app.route('/hello')
    def hello():
        return 'Hello, World!'

    return app

app = create_app()
