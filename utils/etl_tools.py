import os
import requests
import pandas as pd

class ETL_tools:

    def __init__(self):
        pass

    def extract_load(self,url:str,output_folder:str,format:str):
        '''
        This tool extracts the data from API and loads into desired location (output_folder).
        
        Args:
            url: str : API endpoint as source for data extraction
            output_folder: str : the folder where extracted data will be saved
            format: str : the output file format
        
        Returns:
            str: a message indicating success or failure of the operation
        '''

        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__),'..'))
        output_folder = os.path.join(project_root,output_folder)
        format_lower = format.lower()

        try:
               
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()

            filename = os.path.join(output_folder,f"extracted_data.{format_lower}")
            os.makedirs(output_folder,exist_ok=True)

            df = pd.json_normalize(data['results'])

            if format_lower=="csv":
                df.to_csv(filename,index=False)
            elif format_lower=="json":
                        df.to_json(filename,orient="records",lines=True)
            elif format_lower=="parquet":
                        df.to_parquet(filename,index=False)
            else:
                print(f"Invalid or unsupported file format: {format}")

            return f"Data successfully extracted and saved to : {filename}"

        except requests.exceptions.RequestException as e:
              return f"Failed to extract data: {e}"

#,output_folder:str,output_format:str
    def transform_load_context(self,filepath:str):
        '''
        This tool transforms the data from specified file and loads into desired location (output_folder).
        
        Args:
        filepath: str : API endpoint as source for data extraction
        output_folder: str : the folder where extracted data will be saved
        output_format: str : the output file format
        
        Returns:
        str: a message indicating success or failure of the operation
        '''

        file_extension = os.path.splitext(filepath)[1].lower()

        try:

            #output_format_lower = output_format.lower()
            file_extension_lower = file_extension.lower()

            if file_extension_lower==".csv":
                df = pd.read_csv(filepath)
                top_3_rows = str(df.head(3))
                return(f"top 3 rows are:\n {top_3_rows}")

            elif file_extension_lower==".json":
                 df = pd.read_json(filepath,lines=True)
                 top_3_rows = str(df.head(3))
                 return(f"top 3 rows are:\n {top_3_rows}")

            elif file_extension_lower==".parquet":
                 df = pd.read_parquet(filepath)
                 top_3_rows = str(df.head(3))
                 return(f"top 3 rows are:\n {top_3_rows}")
                
            else:
                print(f"Invalid or unsupported file format: {file_extension}")

        except Exception as e:
             return f"Failed to read data: {e}"

    def execute_code(self,code:str)->str:
         """
         This tool executes the provided code and returns the output.

         Args:
            Code: str : Code to be executed
         
         Returns:
            String: str : the output of the executed code on an error string if execution fails
         """

         try:
              exec(code)
              return f"Code executed successfully!"
         except Exception as e:
              return f"Failed to execute the code: {e}"

              
             

if __name__ == "__main__":

      obj = ETL_tools()
      obj.extract_load("https://pokeapi.co/api/v2/pokemon/", "data/extract", "CSV")
      inputpath = "C:\\Gaurav_Prakash\\python_training\\DATA_AGENT\\data\\extract\\extracted_data.csv"
      #outputpath = "C:\\Gaurav_Prakash\\python_training\\DATA_AGENT\\data\\transform"
      output = obj.transform_load_context(inputpath)
      print(output)


