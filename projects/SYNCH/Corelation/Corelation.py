import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import pearsonr
from scipy import stats
from itertools import combinations, product

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)

from DataProcessor.ProcessorClass import ProcessorClass
from Helpers import move_column

class Corelation(ProcessorClass):
    """Run corelatio for each feature within each group."""
    def __init__(self):
        super().__init__(__file__)

    def pearson_corelation(self, df, col_1, col_2):
        """Run a pearson corelation test"""
        
        r, p = pearsonr(df[col_1], df[col_2])
        r2 = r**2

        return pd.DataFrame(
            {
                "title": [col_1] - [col_2],
                "r": [r],
                "p": [p],
                "r2": [r2]
            }
        )

    def collect_results(self, df, method, id_col, compare_pairs):
        groups = [c for c in df.columns if c not in id_col]
        for c in groups:
            s = df[c].astype(str).str.strip().str.replace(",", ".", regex=False)
            df[c] = pd.to_numeric(s, errors="coerce")
        if method == "pearson":
            result_df = pd.concat(
                [self.pearson_corelation(df, a, b) for a, b in combinations(groups, 2)]
            )
        elif method == "repeat_measures":
            result_df = pd.concat(
                [self.repeat_measurement_corelation(df, a, b, id_col[0]) for a, b in combinations(groups, 2)]
            )
        elif method == "lipids_clinic_repeat_measures":
            result_df = pd.concat(
                [self.repeat_measurement_corelation(df, p[0], p[1], id_col[0]) for p in compare_pairs]
            )

        return result_df

    def preprocess_repeat_lipids_df(self, df):
        df = df.iloc[:, 2:]
        df = move_column(df, "treatment_group", 0)
        df = move_column(df, "Time", 0)
        id_counts = df["ID"].value_counts(dropna=False)
        bad_values = id_counts[id_counts != 2].index.tolist()
        if bad_values:
            print(f"These ids are not having correct before/after rows: {bad_values}")
            df = df[~df["ID"].isin(bad_values)]
        synch_subset = df.copy()
        synch_df = synch_subset[synch_subset["treatment_group"] == "Synbiotics"].iloc[:, 2:]
        FMT_subset = df.copy()
        FMT_df = FMT_subset[FMT_subset["treatment_group"] == "Synbiotics + FMT"].iloc[:, 2:]
        placebo_subset = df.copy()
        placebo_df = placebo_subset[placebo_subset["treatment_group"] == "Synbiotics"].iloc[:, 2:]

        return synch_df, FMT_df, placebo_df

    def repeat_measurement_corelation(self, df, col_1, col_2, id_col):
        """Run a repeat measures corelation compare"""
        df = df[[id_col, col_1, col_2]].dropna()

        x = df[col_1] - df.groupby(id_col)[col_1].transform("mean")
        y = df[col_2] - df.groupby(id_col)[col_2].transform("mean")

        n, k = len(df), df[id_col].nunique()
        dof = n - k -1
        r = (x * y).sum() / np.sqrt((x**2).sum() * (y**2).sum())
        t = r * np.sqrt(dof / (1 - r**2))
        p =2 * stats.t.sf(abs(t), dof)

        # 95% CI via Fisher z
        z, se = np.arctanh(r), 1 / np.sqrt(dof - 1)
        ci = np.tanh([z - 1.96 * se, z + 1.96 * se])

        return pd.DataFrame(
            {
                "title": [f"{col_1} - {col_2}"],
                "r": [r],
                "p": [p],
                "dof": [dof],
                "CI95_low": [ci[0]],
                "CI95_high": [ci[1]],
                "n_subjects": [k]
            }
        )

    def preprocess_repeat_clinic_df(self, df_before, df_after, df_lipids):
        # preprocess clinic dataframe
        df_before.columns = df_before.columns.str.replace(r"^before_", "", regex=True)
        df_before = df_before[df_before.columns[:3].tolist() + sorted(df_before.columns[3:])]
        df_after.columns = df_after.columns.str.replace(r"^after_", "", regex=True)
        df_after = df_after[df_after.columns[:3].tolist() + sorted(df_after.columns[3:])]

        if not df_before.columns.equals(df_after.columns):
            missing = set(df_before.columns) - set(df_after.columns)
            extra = set(df_after.columns) - set(df_before.columns)
            raise ValueError(
                f"columns in before and after dataframes are different:"
                f"missing columns: {missing}, extra columns: {extra}"
            )

        union_df = pd.concat([df_before, df_after], ignore_index=True)
        union_df = move_column(union_df, "treatment_group", 0)

        # preprocess lipids dataframe
        df_lipids = df_lipids.iloc[:, 2:]
        df_lipids = move_column(df_lipids, "Time", 0)
        df_lipids = move_column(df_lipids, "treatment_group", 0)
        df_lipids = df_lipids[df_lipids["treatment_group"] != "placebo"]
        id_counts = df_lipids["ID"].value_counts(dropna=False)
        bad_values = id_counts[id_counts != 2].index.tolist()
        if bad_values:
            print(f"These ids are not having correct before/after rows: {bad_values}")
            df_lipids = df_lipids[~df_lipids["ID"].isin(bad_values)]

        # join lipids to clinic for final dataframe
        df_transformed = df_lipids.merge(union_df, on=["ID", "Time", "treatment_group"], how="left")

        synch_subset = df_transformed.copy()
        synch_df = synch_subset[synch_subset["treatment_group"] == "Synbiotics"].iloc[:, 2:]
        FMT_subset = df_transformed.copy()
        FMT_df = FMT_subset[FMT_subset["treatment_group"] == "Synbiotics + FMT"].iloc[:, 2:]

        clinic_columns = union_df.columns[3:].tolist()
        lipids_columns = df_lipids.columns[3:].tolist()

        compare_groups = list(product(clinic_columns, lipids_columns))
       
        return synch_df, FMT_df, compare_groups

    def run(self):
        # For pearson corelation with one group: responder+time+treatment
        # raw_df = self.extract_csv("cleaned_anova_group.csv")
        # df = raw_df.iloc[:, 1:]
        # result_df = self.collect_results(df, "pearson", ["Group"])

        # For RepeatMeasurementCorelation per treatment, lipids dataframe
        # raw_df = self.extract_csv("cleaned_synch_truth_treatmentgroup.csv")
        # synch_df, FMT_df, placebo_df = self.preprocess_repeat_lipids_df(raw_df)
        # synch_result = self.collect_results(synch_df, "repeat_measures", ["ID"])
        # synch_result["treatment"] = "Synbiotics"
        # FMT_result = self.collect_results(FMT_df, "repeat_measures", ["ID"])
        # FMT_result["treatment"] = "Synbiotics + FMT"
        # placebo_result = self.collect_results(placebo_df, "repeat_measures", ["ID"])
        # placebo_result["treatment"] = "placebo"

        # result_df = pd.concat([synch_result, FMT_result, placebo_result], ignore_index=True)
        # flag_df = result_df[(result_df["r"] > 0.6) | (result_df["r"] <- 0.6)]
        # print(flag_df)

        # For RepeatMeasurementCorelation per treatment, lipisd+clinic dataframe
        raw_df_before = self.extract_csv("clinic_before.csv")
        raw_df_after = self.extract_csv("clinic_after.csv")
        raw_df_lipids = self.extract_csv("cleaned_synch_truth_treatmentgroup.csv")
        synch_df, FMT_df, compare_groups = self.preprocess_repeat_clinic_df(raw_df_before, raw_df_after, raw_df_lipids)
        
        synch_result = self.collect_results(synch_df, "lipids_clinic_repeat_measures", ["ID"], compare_groups)
        synch_result["treatment"] = "Synbiotics"
        FMT_result = self.collect_results(FMT_df, "lipids_clinic_repeat_measures", ["ID"], compare_groups)
        FMT_result["treatment"] = "Synbiotics + FMT"

        result_df = pd.concat([synch_result, FMT_result], ignore_index=True)
        flag_df = result_df[(result_df["r"] > 0.6) | (result_df["r"] <- 0.6)]
        print(flag_df)
        
        self.load_csv("repeat_measures_corelation_clinic_results.csv",result_df)

if __name__ =="__main__":
    Corelation().run()