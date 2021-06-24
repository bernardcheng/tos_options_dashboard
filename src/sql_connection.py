# pip install mysql-connector-python-rf
import mysql.connector
from mysql.connector import Error # Insert new data in MYSQL DB

# Import Functionality
def db_connect(db_user, db_pass, db_name, db_url = 'localhost'):
    connection = mysql.connector.connect(
        host=db_url,
        database=db_name,
        user=db_user,
        password=db_pass
    )
    return connection

def sql_import(query, data, user, passwd, db_name):
    try: 
        db_conn = db_connect(user, passwd, db_name)
        cursor = db_conn.cursor()

        print('Executing Query...')
        cursor.execute(query, data)

        # Make sure data is committed to the database
        db_conn.commit()
        db_conn.close()

        print('Data Import Status: Successful!')
        return 
    except Error as error:
        print(error)

def sql_export(query, user, passwd, db_name):
    try: 
        db_conn = db_connect(user, passwd, db_name)
        cursor = db_conn.cursor()
        cursor.execute(query)
        data = cursor.fetchall()
        db_conn.close()
        return data
    except Error as error:
        print(error)