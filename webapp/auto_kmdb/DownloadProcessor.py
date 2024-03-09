from auto_kmdb.Processor import Processor
from auto_kmdb.same_news import same_news
from auto_kmdb.db import get_download_queue, save_download_step, skip_same_news
from auto_kmdb.preprocess import do_replacements, replacements, common_descriptions
from time import sleep
import newspaper


class DownloadProcessor(Processor):
    def process_next(self):
        next_row = get_download_queue()
        if next_row is None:
            sleep(30)
        article = newspaper.Article(next_row['url'])
        article.download()
        article.parse()

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

        if same_news(title, description, text):
            skip_same_news(next_row['id'])
        else:
            save_download_step(next_row['id'], text, title, description)
