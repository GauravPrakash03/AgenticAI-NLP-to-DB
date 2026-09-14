import psycopg2
import os

from dotenv import load_dotenv
load_dotenv()

if 'port' not in os.environ:
    os.environ['port']='5432'

''' CONFIGURATION '''

DB_CONFIG = {
    "host": os.environ['host'],
    "port": int(os.environ['port']),
    "database": os.environ['database'],
    "user": os.environ['user'],
    "password": os.environ['password']
}

class DatabaseUtil:

    def __init__(self,dbconfig):
         self.dbconfig = dbconfig

         try:
             self.connection = psycopg2.connect(**dbconfig)
         except Exception as e:
             print(f"Connection not successful, error: {e}")
             self.connection=None

    def schema_details(self,schema_name):

        connection = self.connection
        cursor = None
        schema_info_context = ""

        try:
            if connection is None:
                return "Database connection is not available."

            cursor = connection.cursor()

            # Adding Tables list

            schema_info_context = f"Database schema: {schema_name}\n"

            cursor.execute("select table_name from information_schema.tables where table_schema=%s;", (schema_name,))
            tables_list = cursor.fetchall()

            schema_info_context += "Tables:\n"
            for tables in tables_list:
                table_name = tables[0]
                schema_info_context = f"{schema_info_context}\nTable: {table_name}\n"

                # Adding columns and data types

                cursor.execute("select column_name, data_type from information_schema.columns where table_name=%s;", (table_name,))
                columns_list = cursor.fetchall()

                for column in columns_list:
                    column_name = column[0]
                    data_type = column[1]
                    schema_info_context = f"{schema_info_context} Column: {column_name}, Data Type: {data_type}\n"

                # Adding sample data
                cursor.execute(f"select * from {schema_name}.{table_name} limit 5;")
                sample_data = cursor.fetchall()
                connection.commit()
                schema_info_context = f"{schema_info_context} Sample Data:\n"
                for row in sample_data:
                    schema_info_context = f"{schema_info_context}  {row}\n"

        except Exception as e:
             print(f"Error fetching schema details: {e}")
             schema_info_context = f"Error fetching schema details {e}"

        finally:
             if cursor is not None:
                  cursor.close()
             if connection is not None:
                  connection.close()

        return schema_info_context

    def execute_query(self, query):
        connection = self.connection
        cursor = None
        schema_info_context = ""
        try:
            if connection is None:
                return "Database connection is not available."
            cursor = connection.cursor()

            # Execute SQL query
            
            cursor.execute(query)
            result = cursor.fetchall()
            connection.commit()

            return str(result)

        except Exception as e:
            print(f"Eror fetching executing query: {e}")
            return None

        finally:
            if cursor is not None:
                cursor.close()
                if connection is not None:
                    connection.close()



obj = DatabaseUtil(dict(DB_CONFIG))

'''obj = DatabaseUtil({
    "host": os.environ['host'],
    "port": int(os.environ['port']),
    "database": os.environ['database'],
    "user": os.environ['user'],
    "password": os.environ['password']
})'''

result = obj.schema_details("public")

with open("test_schema_details.txt", "w") as f:
     f.write(result)

