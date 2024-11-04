import sys
import csv
import mysql.connector
import os


if len(sys.argv) < 2:
    print('nem adtál meg csv fájlt')
    exit(0)

with open(sys.argv[1], newline='') as csvfile:
    reader = csv.DictReader(csvfile)
    aliases = {f:[] for f in reader.fieldnames}
    for d in reader:
        for k, v in d.items():
            if v:
                aliases[k].append(v)

connection_pool = mysql.connector.pooling.MySQLConnectionPool(
  pool_name="cnx_pool",
  pool_size=1,
  pool_reset_session=True,
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

with connection_pool.get_connection() as connection:
    delete = 'DELETE FROM autokmdb_alias_place'
    with connection.cursor(dictionary=True) as cursor:
        cursor.execute(delete)

    for k, v in aliases.items():
        if k == 'rész típus':
            continue
        query = 'SELECT place_id FROM news_places WHERE name_hu = %s'
        insert = 'INSERT INTO autokmdb_alias_place (place_id, alias_name) VALUES (%s, %s)'
        with connection.cursor(dictionary=True) as cursor:
            cursor.execute(query, (k,))
            result = cursor.fetchone()
            if not result:
                print('név nem létezik:', k)
                continue
            place_id = result['place_id']
            print(place_id)
            for alias_name in v:
                cursor.execute(insert, (place_id, alias_name))

    connection.commit()
