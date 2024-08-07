from dotenv import load_dotenv

load_dotenv()

from flask import Flask
from threading import Thread
import os
from time import sleep
import traceback

sleep(10)  # TODO better wait handling
from auto_kmdb.DownloadProcessor import DownloadProcessor, do_retries, login_444, login_24
from auto_kmdb.ClassificationProcessor import ClassificationProcessor
from auto_kmdb.NERProcessor import NERProcessor
from auto_kmdb.KeywordProcessor import KeywordProcessor
from auto_kmdb.rss_watcher import rss_watcher
import logging


logger = logging.getLogger(__name__)


def create_app():
    logfile = "autokmdb.log"
    if "LOGFILE" in os.environ:
        logfile = os.environ["LOGFILE"]
    logging.basicConfig(filename=logfile, level=logging.INFO)
    for _ in range(10):
        logger.info("")
    logger.info("Started")

    app = Flask(
        __name__,
        instance_relative_config=True,
    )

    with app.app_context():
        from auto_kmdb.routes import api

        app.register_blueprint(api)
        logger.info("registered api")

    try:
        login_444()
    except Exception:
        logging.error(traceback.format_exc())
    try:
        login_24()
    except Exception:
        logging.error(traceback.format_exc())
        print(traceback.format_exc())
    Thread(target=rss_watcher, args=(app.app_context(),), daemon=True).start()
    Thread(target=do_retries, args=(app.app_context(),), daemon=True).start()

    processors = [
        DownloadProcessor(),
        ClassificationProcessor(),
        NERProcessor(),
        KeywordProcessor(),
    ]
    for processor in processors:
        processor.load_model()
        Thread(target=processor.process_loop, args=(), daemon=True).start()

    @app.route("/hello")
    def hello():
        return "Hello, World!"

    return app


app = create_app()
