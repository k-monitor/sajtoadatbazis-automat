import mysql.connector
import jsonlines
import os

# Connect to MySQL database
mysql_db = mysql.connector.connect(
  host=os.environ["MYSQL_HOST"],
  port=os.environ["MYSQL_PORT"],
  user=os.environ["MYSQL_USER"],
  password=os.environ["MYSQL_PASS"],
  database=os.environ["MYSQL_DB"],
)

# Create a cursor object
with mysql_db.cursor(dictionary=True) as cursor, jsonlines.open('place_parents.jsonl', 'w') as writer:
    cursor.execute('SET SESSION group_concat_max_len = 10000;')
    query = """
    SELECT place_id, parent_id, name_hu AS name
    FROM news_places
    WHERE status = 'Y'
    """
    # LIMIT 10;
    cursor.execute(query)
    rows = cursor.fetchall()
    writer.write_all(rows)

l = []
places = dict()
top_places = set()

with jsonlines.open('place_parents.jsonl') as reader:
    for row in reader:
        places[row['place_id']]=row
        l.append(row)

def get_recursive_name(place_id):
    name = places[place_id]['name']
    if places[place_id]['parent_id']:
        return get_recursive_name(places[place_id]['parent_id'])+'/'+name
    return name

with jsonlines.open('place_trees.jsonl', 'w') as writer:
    for place in l:
        place['recursive_name'] = get_recursive_name(place['place_id'])
        top_place = place['recursive_name'].split('/')[0]
        if top_place == 'Európa' and len(place['recursive_name'].split('/')) > 1:
            top_place = place['recursive_name'].split('/')[1]
        top_places.add(top_place)
        writer.write(place)

with jsonlines.open('top_places.jsonl', 'w') as writer:
    writer.write_all([{'name': p, 'category': ''} for p in top_places])
