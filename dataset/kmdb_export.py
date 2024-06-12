import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os
import jsonlines

load_dotenv('../webapp/.env')


def get_news_data():
    try:
        connection = mysql.connector.connect(
            host=os.environ["MYSQL_HOST"],
            port=os.environ["MYSQL_PORT"],
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASS"],
            database=os.environ["MYSQL_DB"],
        )
        if connection.is_connected():
            cursor = connection.cursor(dictionary=True)

            query_news = """
                SELECT
                    n.news_id,
                    nl.name AS title,
                    n.source_url,
                    CONCAT('kmdb://', n.news_id) AS kmdb_url,
                    n.source AS newspaper,
                    FROM_UNIXTIME(n.pub_time) AS pub_time
                FROM
                    news_news n
                LEFT JOIN
                    news_lang nl ON n.news_id = nl.news_id
            """
            cursor.execute(query_news)
            news_data = cursor.fetchall()

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

            def map_related_data(news_list, related_data, key):
                for news in news_list:
                    news[key] = [item['name'] for item in related_data if item['news_id'] == news['news_id']]

            for news in news_data:
                news['pub_time'] = news['pub_time'].strftime('%Y-%m-%d %H:%M:%S') if news['pub_time'] else ''
            print('running map')
            map_related_data(news_data, persons_data, 'persons')
            map_related_data(news_data, institutions_data, 'institutions')
            map_related_data(news_data, places_data, 'places')
            map_related_data(news_data, others_data, 'others')

            return news_data

    except Error as e:
        print(f"Error: {e}")
    finally:
        if connection.is_connected():
            cursor.close()
            connection.close()


news_data = get_news_data()

with jsonlines.open('kmdb_news_dump.jsonl', mode='w') as writer:
    writer.write_all(news_data)
