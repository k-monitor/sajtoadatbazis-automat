from bs4 import BeautifulSoup
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import jsonlines
from datasets import Dataset


base_dir = os.path.dirname(os.path.abspath(__file__)) + "/"


def export_kmdb(connection, limit=-1):
    try:
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            limit_part = f"LIMIT {limit}" if limit >= 0 else ""

            query_news = f"""
                SELECT
                    n.news_id,
                    nl.name AS title,
                    nl.teaser as description,
                    articletext as text,
                    n.source_url,
                    n.archive_url,
                    CONCAT('https://adatbazis.k-monitor.hu/', nl.seo_url_default) AS kmdb_url,
                    nn.name AS newspaper,
                    nclg.alias AS category,
                    FROM_UNIXTIME(n.pub_time) AS pub_time
                FROM
                    news_news n
                INNER JOIN
                    news_lang nl ON n.news_id = nl.news_id
                LEFT JOIN
                    news_newspapers_link nnl ON n.news_id = nnl.news_id
                LEFT JOIN
                    news_newspapers nn ON nnl.newspaper_id = nn.newspaper_id
                LEFT JOIN
                    news_categories_link ncl ON n.news_id = ncl.news_id
                LEFT JOIN
                    news_categories_lang nclg ON ncl.cid = nclg.cid
                WHERE n.status = 'Y'
                GROUP BY
                    n.news_id
                {limit_part}
            """
            cursor.execute(query_news)

            def transform_article(article):
                # article['files'] = article['files'].split(
                # ';;;') if article['files'] else []
                try:
                    soup = BeautifulSoup(article["text"], features="lxml")
                    article["text"] = "\n".join([t.text for t in soup.find_all("p")])
                except Exception:
                    article["text"] = ""
                return article

            news_data = [transform_article(article) for article in cursor.fetchall()]

            query_persons = """
                SELECT
                    pl.news_id, p.name
                FROM
                    news_persons_link pl
                JOIN
                    news_persons p ON pl.person_id = p.person_id
            """
            cursor.execute(query_persons)
            persons_data = cursor.fetchall()

            query_files = """
                SELECT
                    DISTINCT nfl.news_id, nf.name_hu as name
                FROM
                    news_files_link nfl
                JOIN
                    news_files nf ON nfl.file_id = nf.file_id
            """
            cursor.execute(query_files)
            files_data = cursor.fetchall()

            query_institutions = """
                SELECT
                    il.news_id, i.name
                FROM
                    news_institutions_link il
                JOIN
                    news_institutions i ON il.institution_id = i.institution_id
            """
            cursor.execute(query_institutions)
            institutions_data = cursor.fetchall()

            query_places = """
                SELECT
                    pl.news_id, p.name_hu AS name
                FROM
                    news_places_link pl
                JOIN
                    news_places p ON pl.place_id = p.place_id
            """
            cursor.execute(query_places)
            places_data = cursor.fetchall()

            query_others = """
                SELECT
                    ol.news_id, o.name
                FROM
                    news_others_link ol
                JOIN
                    news_others o ON ol.other_id = o.other_id
            """
            cursor.execute(query_others)
            others_data = cursor.fetchall()

            def create_related_data_dict(related_data):
                related_dict = {}
                for item in related_data:
                    if item["news_id"] not in related_dict:
                        related_dict[item["news_id"]] = []
                    related_dict[item["news_id"]].append(item["name"])
                return related_dict

            persons_dict = create_related_data_dict(persons_data)
            institutions_dict = create_related_data_dict(institutions_data)
            places_dict = create_related_data_dict(places_data)
            others_dict = create_related_data_dict(others_data)
            files_dict = create_related_data_dict(files_data)

            for news in news_data:
                news["pub_time"] = (
                    news["pub_time"].strftime("%Y-%m-%d %H:%M:%S")
                    if news["pub_time"]
                    else ""
                )
                news_id = news["news_id"]
                news["persons"] = persons_dict.get(news_id, [])
                news["institutions"] = institutions_dict.get(news_id, [])
                news["places"] = places_dict.get(news_id, [])
                news["others"] = others_dict.get(news_id, [])
                news["files"] = files_dict.get(news_id, [])

            return news_data

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()


load_dotenv(base_dir + "../../webapp/.env.prod")

with mysql.connector.connect(
    host=os.environ["MYSQL_HOST"],
    port=os.environ["MYSQL_PORT"],
    user=os.environ["MYSQL_USER"],
    password=os.environ["MYSQL_PASS"],
    database=os.environ["MYSQL_DB"],
) as connection:
    data = export_kmdb(connection)

with jsonlines.open(base_dir + "export.prod.jsonl", mode="w") as writer:
    writer.write_all(data)

dataset = Dataset.from_list(data)
dataset.push_to_hub("K-Monitor/kmdb_base")

files_list = []
for f in dataset["files"]:
    if f:
        files_list += f

files_set = set(files_list)

print(len(files_set))
