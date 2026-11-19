import os
import sys
import numpy as np
import pandas as pd
from scipy.stats import ttest_rel
from statsmodels.stats.multitest import multipletests

basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)

from DataProcessor.ProcessorClass import ProcessorClass

class PairedTTests(ProcessorClass):
    """Run paired t-tests for each feature within each group."""

    def __init__(self):
        super().__init__(__file__)
        # set specific time value and order
        self.timepoints = ("Before", "After")

    def run_paired_tests(self, df, subject_col: str="ID", group_col: str="Group", time_col:str="Time"):
        observed_timepoints = set(df[time_col].dropna().unique())
        if observed_timepoints != set(self.timepoints):
            raise ValueError(
                f"Timepoints are not correct: expected{self.timepoints}, found{sorted(observed_timepoints, key=str)}"
            )

        metadata_cols = set([subject_col, group_col, time_col])
        feature_cols = [col for col in df.columns if col not in metadata_cols]

        results = []

        for group_name, group_df in df.groupby(
            group_col,
            dropna=True,
            sort=False,
        ):
            for feature in feature_cols:
                working_df = group_df[
                    [subject_col, time_col, feature]
                ].copy()

                working_df[feature] = pd.to_numeric(working_df[feature], errors='coerce')
                working_df = working_df.dropna(subset=[subject_col, time_col, feature])

                paired_values = (
                    working_df.pivot(
                        index=subject_col,
                        columns=time_col,
                        values=feature,
                    )
                    .reindex(columns=self.timepoints)
                    .dropna(subset=list(self.timepoints))
                )

                values_time1 = paired_values[self.timepoints[0]].to_numpy()
                values_time2 = paired_values[self.timepoints[1]].to_numpy()
                n_pairs = len(paired_values)

                if n_pairs >= 2:
                    test_result = ttest_rel(values_time2, values_time1)
                    t_statistic = float(test_result.statistic)
                    p_value = float(test_result.pvalue)
                    mean_time1 = float(np.mean(values_time1))
                    mean_time2 = float(np.mean(values_time2))
                    mean_difference = float(np.mean(values_time2 - values_time1))
                else:
                    t_statistic = np.nan
                    p_value = np.nan
                    mean_time1 = (float(np.mean(values_time1)) if n_pairs else np.nan)
                    mean_time2 = (float(np.mean(values_time2)) if n_pairs else np.nan)
                    mean_difference = (float(np.mean(values_time2 - values_time1)) if n_pairs else np.nan)

                results.append({
                    "Lipid": feature,
                    "Group": group_name,
                    "Time1": self.timepoints[0],
                    "Time2": self.timepoints[1],
                    "N_Pairs": n_pairs,
                    "Mean_Time1": mean_time1,
                    "Mean_Time2": mean_time2,
                    "Mean_Difference": mean_difference,
                    "T_Statistic": t_statistic,
                    "P_Value": p_value,
                })

        result_df = pd.DataFrame(results)
        result_df["q_value"] = np.nan

        valid_p_values = result_df["P_Value"].notna()
        if valid_p_values.any():
            result_df.loc[valid_p_values, "q_value"] = multipletests(
                result_df.loc[valid_p_values, "P_Value"],
                method="fdr_bh"
            )[1]

        return result_df

    def run(self):
        raw_df = self.extract_csv("cleaned_synch_truth_treatmentgroup.csv")
        result_df = self.run_paired_tests(raw_df, subject_col="ID", group_col="treatment_group", time_col="Time")
        ttest_sig = result_df[result_df["P_Value"]<0.05]
        self.load_csv("paired_t_test_results_sig_withoutresponder.csv",ttest_sig)
        self.load_csv("paired_t_test_results_withoutresponder.csv", result_df)

if __name__ =="__main__":
    PairedTTests().run()