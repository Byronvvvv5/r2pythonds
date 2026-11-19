import pandas as pd
import numpy as np
import os
import sys
from datetime import datetime
from sklearn.preprocessing import MinMaxScaler

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from DataProcessor.ProcessorClass import ProcessorClass

from Helpers import move_column, enforce_numeric_datatype, detect_changes_between_dataframes
from Schema.sample_schema import SampleSchema

IMPUTED_INPUT = 'df_final_imputed.csv'
CONTROL_GROUP_LIST = 'TRUTH-placebo arm.txt'
TREATMENT_INPUT = 'SYNCH_Masterfile for SYNCH lipidomics only.xlsx'
RESPONDER_LIST = "Responders.txt"

class Cleaning(ProcessorClass):
    """This class includes methods for loading excel files, mergeing multiple files, droping duplicates and filtering."""

    def __init__(self):
        super().__init__(__file__)
        self.output_copy_path_1 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'PCA', 'input')
        self.output_copy_path_2 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'ANOVA', 'input')
        self.output_copy_path_3 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'PairedTTests', 'input')
        self.output_copy_path_4 = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'Corelation', 'input')


        self.imputed_df = self.extract_csv(IMPUTED_INPUT)
        self.control_list = self.extract_txt(CONTROL_GROUP_LIST).iloc[:, 0].tolist()
        self.treatment_df = self.extract_excel(TREATMENT_INPUT)
        self.responder_df = self.extract_txt(RESPONDER_LIST, sep=";", skipinitialspace=True)

    def add_control_group(self):
        # remove TRUTH group which are not in list        
        df_selected = self.imputed_df[
            (self.imputed_df["Study"] == "SYNCH") 
            |
            (self.imputed_df["ID"].astype(str).isin([str(x) for x in self.control_list]))
        ]

        df_selected = df_selected.rename(columns={"Label": "Time"})

        return df_selected

    def scale(self, df):
        lipid_cols = df.columns[4:]

        scaler = MinMaxScaler()
        df_scaled = df.copy()
        df_scaled[lipid_cols] = scaler.fit_transform(df[lipid_cols])

        return df_scaled

    def add_treatment_group(self, df):
        df_treatment_naming = self.treatment_df.iloc[:, :2]
        df_treatment_naming = df_treatment_naming.rename(columns={"id": "ID"})

        df_scaled = df.copy()
        df_combined = df_scaled.merge(df_treatment_naming, on="ID", how="left")
        df_combined.loc[df_combined["Study"] == "TRUTH", "treatment_group"] = "placebo"
        df_result = move_column(df_combined, "treatment_group", 4)

        df_result['Time'] = df_result['Time'].map({
            'Baseline': 'Before',
            'v2': 'Before',
            '24 WEEKS': 'After',
            'v5': 'After'
        })

        self.load_csv('cleaned_synch_truth_treatmentgroup.csv', df_result)
        self.copy_output_file('cleaned_synch_truth_treatmentgroup.csv', self.output_copy_path_1)

        # add responders:
        list_fmt = [str(x).strip() for x in self.responder_df['FMT'].iloc[0].split(",")]
        list_tr = [str(x).strip() for x in self.responder_df['TRUTH-placebo'].iloc[0].split(",")]
        list_syn = [str(x).strip() for x in self.responder_df['Synbiotics'].iloc[0].split(",")]
        
        df_result["Responder"] = np.where(
            (
                ((df_result["treatment_group"] == "Synbiotics + FMT") &
                (df_result["ID"].astype(str).isin(list_fmt)))
            ) |
            (
                ((df_result["treatment_group"] == "placebo") &
                (df_result["ID"].astype(str).isin(list_tr)))
            ) |
            (
                ((df_result["treatment_group"] == "Synbiotics") &
                (df_result["ID"].astype(str).isin(list_syn)))
            ),
            "Yes",
            "No"
        )
        df_result = move_column(df_result, "Responder", 5)

        # prep paired t test dataframe with combined group column
        df_paired = df_result.copy()
        df_paired["Group"] = df_paired["Responder"] + "-" + df_paired["treatment_group"]
        # df_paired = df_paired.iloc[:, 6:]
        df_paired = move_column(df_paired, "Group", 0)
        self.load_csv('cleaned_paired_ttest_treatmentgroup.csv', df_paired)
        self.copy_output_file('cleaned_paired_ttest_treatmentgroup.csv', self.output_copy_path_3)
        print(df_paired["Group"].unique())
        
        # prep anova dataframe with combined group column
        df_anova = df_result.copy()
        df_anova["Group"] = df_anova["Responder"] + "-" + df_anova["Time"] + "-" + df_anova["treatment_group"]
        df_anova = df_anova.iloc[:, 6:]
        df_anova = move_column(df_anova, "Group", 0)

        self.load_csv('cleaned_anova_group.csv', df_anova)
        self.copy_output_file('cleaned_anova_group.csv', self.output_copy_path_2)
        self.copy_output_file('cleaned_anova_group.csv', self.output_copy_path_4)
        print(df_anova["Group"].unique())

    def run(self):
        df_selected = self.add_control_group()
        df_scaled = self.scale(df_selected)
        self.add_treatment_group(df_scaled)



if __name__ == "__main__":
    Cleaning().run()