from auto_kmdb.Processor import Processor
from auto_kmdb.same_news import same_news
from auto_kmdb.db import get_download_queue, save_download_step, skip_same_news, skip_download_error
from auto_kmdb.preprocess import do_replacements, replacements, common_descriptions
from time import sleep
import newspaper
from auto_kmdb.db import connection_pool


class DownloadProcessor(Processor):
    def __init__(self):
        pass
        # super().__init__()

    def process_next(self):
        with connection_pool.get_connection() as connection:
            next_row = get_download_queue(connection)
        print('Downloading')
        if next_row is None:
            sleep(30)
            return

        print('Downloading', next_row['url'])
        article = newspaper.Article(next_row['url'])
        try:
            article.download()
            article.parse()
        except Exception as e:
            print(e)
            with connection_pool.get_connection() as connection:
                skip_download_error(connection, next_row['id'])
            return

        title = do_replacements(article.title, replacements)
        text = do_replacements(article.text, replacements)

        description = article.meta_description
        for common_description in common_descriptions:
            description = description.replace(common_description.strip(), '')

        if len(description) < 1 and text.count('\n') > 1:
            sl = text.splitlines()[0]
            description = sl[:sl[:400].rfind('.')+1]
            if '.' not in sl[:400]:
                description = sl[:400]

        date = article.publish_date
        if date is not None:
            date = date.strftime('%Y. %m. %d. %H:%M:%S')
        else:
            date = ''

        if same_news(title, description, text) and next_row['source'] != 1:
            with connection_pool.get_connection() as connection:
                skip_same_news(connection, next_row['id'], text, title, description)
        else:
            with connection_pool.get_connection() as connection:
                save_download_step(connection, next_row['id'], text, title, description)
