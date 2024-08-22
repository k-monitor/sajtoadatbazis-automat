import json
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv
import os

load_dotenv('../webapp/.env.prod')

def connect_to_database():
    try:
        connection = mysql.connector.connect(
            host=os.environ["MYSQL_HOST"],
            port=os.environ["MYSQL_PORT"],
            user=os.environ["MYSQL_USER"],
            password=os.environ["MYSQL_PASS"],
            database=os.environ["MYSQL_DB"],
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print(f"Error while connecting to MySQL: {e}")
    return None

def create_table(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS autokmdb_keyword_synonyms (
            id INT AUTO_INCREMENT PRIMARY KEY,
            synonym VARCHAR(255),
            name VARCHAR(255),
            db_id INT
        ) CHARACTER SET utf8 COLLATE utf8_general_ci;
        """)
        print("Table 'autokmdb_keyword_synonyms' created successfully.")
    except Error as e:
        print(f"Error while creating table: {e}")
    finally:
        if cursor:
            cursor.close()

def insert_data(connection, data):
    try:
        cursor = connection.cursor()
        for item in data:
            sql = """INSERT INTO autokmdb_keyword_synonyms (synonym, name, db_id) 
                     VALUES (%s, %s, %s)"""
            values = (item['synonym'], item['name'], item['db_id'])
            cursor.execute(sql, values)
        connection.commit()
        print(f"Successfully inserted {cursor.rowcount} rows.")
    except Error as e:
        print(f"Error while inserting data: {e}")
    finally:
        if cursor:
            cursor.close()

def main():
    # Read JSON file
    with open('keyword_synonyms.json', 'r', encoding='utf-8') as file:
        data = json.load(file)
    
    # Connect to the database
    connection = connect_to_database()
    if connection is None:
        return
    
    # Create table
    create_table(connection)
    
    # Insert data
    insert_data(connection, data)
    
    # Close the connection
    if connection.is_connected():
        connection.close()
        print("MySQL connection is closed")

if __name__ == "__main__":
    main()