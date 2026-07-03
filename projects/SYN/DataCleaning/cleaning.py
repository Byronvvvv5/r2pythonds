# First step of this project: Data Cleaning. 
# This script will load the excel files(including exported data from Mzquality and a sample info file), clean up the data 
# (including filter records, rename columns, extract column values, deduplicate columns and enforce schema),
# and merge them into one result dataframe. 
# The final output will be saved as csv file in the output folder, and also copied to the Preprocessing/input folder for the next step.
import pandas as pd
import os
import sys

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from DataProcessor.ProcessorClass import ProcessorClass

from Helpers import enforce_schema, detect_changes_between_dataframes
from Schema import SampleSchema, HighPHSchema, LowPHSchema

# Customized unwanted columns in input files
UNWANTEDCOLUMNS = ['Batch']
# Everytime running new preprocess, please load files to input directory and update the PROCESSFILES list
PROCESSFILES = ['sample.xlsx', 'highPH.xlsx', 'lowPH.xlsx']

class Cleaning(ProcessorClass):
    """This class includes methods for loading excel files, mergeing multiple files, droping duplicates and filtering."""

    def __init__(self):
        super().__init__(__file__)
        self.output_copy_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Preprocessing', 'input')
        self.dataframes = {}

    def preprocess(self):
        """Preprocess the data loaded, cleanup and merge."""
        for file_name in PROCESSFILES:
            self.dataframes[file_name] = self.extract_excel(file_name)

        df_sample = self.dataframes['sample.xlsx']
        df_highPH = self.dataframes['highPH.xlsx']
        df_lowPH = self.dataframes['lowPH.xlsx']

        # filter unwanted columns of highPH and lowPH
        df_highPH = df_highPH.drop(columns=UNWANTEDCOLUMNS, errors='ignore')
        df_lowPH = df_lowPH.drop(columns=UNWANTEDCOLUMNS, errors='ignore')
        
        # rename columns of highPH and lowPH to match sample
        df_highPH.columns = df_highPH.columns.str.slice(4)
        df_lowPH.columns = df_lowPH.columns.str.slice(4)
        
        # give the first column a name
        df_highPH.columns.values[0] = 'injectionID'
        df_lowPH.columns.values[0] = 'injectionID'

        # Extract only the numeric part of injectionID in both DataFrames before merging
        df_highPH['injectionID'] = df_highPH['injectionID'].astype(str).str.extract(r'_(\d+)_')[0].str.lstrip('0')
        df_lowPH['injectionID'] = df_lowPH['injectionID'].astype(str).str.extract(r'_(\d+)_')[0].str.lstrip('0')

        # Remove duplicate columns from highPH that are also in lowPH
        unique_columns = ['injectionID'] + list(set(df_highPH.columns) - set(df_lowPH.columns) - {'injectionID'})
        df_highPH = df_highPH[unique_columns]
        
        # Ensure schema for dataframes, question should this injectionID be str or int?
        df_sample = enforce_schema(df_sample, SampleSchema)
        df_highPH = enforce_schema(df_highPH, HighPHSchema)
        df_lowPH = enforce_schema(df_lowPH, LowPHSchema)
        
        # Join highPH and lowPH DataFrames and include all the columns based on injectionID
        df_test = df_lowPH.merge(df_highPH, on='injectionID', how='outer')
        
        # Compare the number of rows to decide the left DataFrame for the join
        if df_sample.shape[0] <= df_test.shape[0]:
            df_final = df_sample.merge(df_test, on='injectionID', how='left')
        else:
            df_final = df_test.merge(df_sample, on='injectionID', how='left')
        
        self.load_csv('merged_DataCleaning_output.csv', df_final)
        self.copy_output_file('merged_DataCleaning_output.csv', self.output_copy_path)

        return df_final


    def test(self):
        """Test the class methods."""
        # Example test method
        df1 = self.extract_excel('sample.xlsx')
        df2 = self.extract_excel('sample.xlsx')

        # Add a new column with all values set to 'test' for testing purpose
        df2['NewColumn'] = 'test'
        # Change the value of a specific cell for testing purpose
        df2.loc[1, 'Group'] = 'TESTING'

        # This is the check columns list, and will be included in the result_df
        columns_list = df2.columns.tolist()

        # This is the demo of how to compare 2 dataframes, the result will contain check_columns and 2 new columns change_type, changes
        df = detect_changes_between_dataframes(
            df1,
            df2,
            check_columns=columns_list,
            unique_key='SampleID',
            detect_column_changes=True
        )
        # print out to verify the changes
        print(df.to_string(index=False))

    def run(self):
        """Run the preprocessing."""
        result = self.preprocess()
        print(result.shape)
        # Uncomment the following line to run the test method
        # self.test()
    

if __name__ == "__main__":
    Cleaning().run()
