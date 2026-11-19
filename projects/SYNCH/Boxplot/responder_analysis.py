import os
import re
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from DataProcessor.ProcessorClass import ProcessorClass

from Helpers import enforce_numeric_datatype


class ResponderAnalysis(ProcessorClass):
    """Compare lipid change scores (After - Before) between responders and non-responders per treatment group."""

    def __init__(self):
        super().__init__(__file__)
        self.change_output_path = os.path.join(self.output_path, "change_comparison")
        os.makedirs(self.change_output_path, exist_ok=True)

        self.group_order = ["placebo", "Synbiotics", "Synbiotics + FMT"]
        self.responder_order = ["Non-responder", "Responder"]
        self.metadata_cols = ["ID", "Time", "Responder", "treatment_group", "Group"]
        self.responder_labels = {
            "Yes": "Responder",
            "No": "Non-responder",
            "yes": "Responder",
            "no": "Non-responder"
        }

    def derive_responder_and_treatment(self, df):
        """
        Make sure Responder and treatment_group columns exist.

        Supports either separate Responder/treatment_group columns, or a combined
        Group column such as 'Yes-Synbiotics'.
        """
        df = df.copy()

        if "Responder" not in df.columns:
            if "Group" not in df.columns:
                raise ValueError(
                    "The dataset must contain either a Responder column "
                    "or a Group column."
                )
            df["Responder"] = (
                df["Group"]
                .astype(str)
                .str.extract(r"^(Yes|No)", expand=False)
                .map({"Yes": "Responder", "No": "Non-responder"})
            )

        if "treatment_group" not in df.columns:
            if "Group" not in df.columns:
                raise ValueError(
                    "The dataset must contain a treatment_group column "
                    "or a combined Group column."
                )
            df["treatment_group"] = (
                df["Group"]
                .astype(str)
                .str.replace(r"^(Yes|No)-", "", regex=True)
            )

        df["Responder"] = df["Responder"].replace(self.responder_labels)

        return df

    def get_lipid_columns(self, df):
        """All columns that are not metadata are treated as lipids."""
        metadata_cols = [col for col in self.metadata_cols if col in df.columns]
        return [col for col in df.columns if col not in metadata_cols]

    def prepare_data(self, df):
        """Derive responder/treatment columns and make lipid columns numeric. Returns data, lipid_list."""
        data = self.derive_responder_and_treatment(df)
        lipid_list = self.get_lipid_columns(data)
        print(f"Number of lipid columns: {len(lipid_list)}")

        data = enforce_numeric_datatype(data, lipid_list)

        return data, lipid_list

    def calculate_change_for_lipid(self, df, lipid):
        """Individual-level change score (After - Before) for one lipid; None if not both timepoints exist."""
        key_cols = ["ID", "Responder", "treatment_group", "Time"]
        working_df = df[key_cols + [lipid]].dropna(subset=key_cols + [lipid])

        # One row per participant, Before/After as columns
        paired_df = working_df.pivot(
            index=["ID", "Responder", "treatment_group"],
            columns="Time",
            values=lipid
        )

        if not {"Before", "After"}.issubset(paired_df.columns):
            return None

        paired_df = paired_df.dropna(subset=["Before", "After"])
        paired_df["Difference"] = paired_df["After"] - paired_df["Before"]
        paired_df = paired_df.reset_index()
        paired_df["Lipid"] = lipid

        return paired_df

    def calculate_change_scores(self, data, lipid_list):
        """Change scores for all lipids in one long table."""
        change_results = []

        for lipid in lipid_list:
            paired_df = self.calculate_change_for_lipid(data, lipid)
            if paired_df is not None:
                change_results.append(paired_df)

        if not change_results:
            raise ValueError(
                "No paired data could be generated. Check ID and Time columns."
            )

        return pd.concat(change_results, ignore_index=True)

    def compare_responder_change(self, group_df, lipid, treatment):
        """Welch's t-test of change scores: responders vs non-responders within one treatment group."""
        responder_values = group_df.loc[
            group_df["Responder"] == "Responder", "Difference"
        ].dropna()
        nonresponder_values = group_df.loc[
            group_df["Responder"] == "Non-responder", "Difference"
        ].dropna()

        n_responder = len(responder_values)
        n_nonresponder = len(nonresponder_values)

        if n_responder >= 2 and n_nonresponder >= 2:
            test_result = ttest_ind(responder_values, nonresponder_values, equal_var=False)
            t_statistic = test_result.statistic
            p_value = test_result.pvalue
        else:
            t_statistic = np.nan
            p_value = np.nan

        mean_responder = responder_values.mean() if n_responder > 0 else np.nan
        mean_nonresponder = nonresponder_values.mean() if n_nonresponder > 0 else np.nan

        return {
            "Lipid": lipid,
            "treatment_group": treatment,
            "N_Responder": n_responder,
            "N_Non_responder": n_nonresponder,
            "Mean_Change_Responder": mean_responder,
            "Mean_Change_Non_responder": mean_nonresponder,
            "Mean_Difference_between_groups": mean_responder - mean_nonresponder,
            "T_Statistic": t_statistic,
            "P_Value": p_value
        }

    def add_q_values(self, stats_df):
        """BH FDR correction across all lipid-treatment comparisons with a valid p-value."""
        stats_df = stats_df.copy()
        stats_df["q_value"] = np.nan

        valid_p = stats_df["P_Value"].notna()
        if valid_p.any():
            stats_df.loc[valid_p, "q_value"] = multipletests(
                stats_df.loc[valid_p, "P_Value"],
                method="fdr_bh"
            )[1]

        return stats_df

    def run_responder_tests(self, change_df, lipid_list):
        """Run responder vs non-responder tests for every lipid and treatment group, then add q-values."""
        stat_results = []

        for lipid in lipid_list:
            lipid_df = change_df[change_df["Lipid"] == lipid]

            for treatment in lipid_df["treatment_group"].dropna().unique():
                group_df = lipid_df[lipid_df["treatment_group"] == treatment]
                stat_results.append(self.compare_responder_change(group_df, lipid, treatment))

        return self.add_q_values(pd.DataFrame(stat_results))

    def add_comparison_annotation(self, ax, x_center, y, height, p, q):
        """Draw a bracket with p- and q-value above one treatment group."""
        ax.plot(
            [x_center - 0.18, x_center - 0.18, x_center + 0.18, x_center + 0.18],
            [y, y + height, y + height, y],
            color="black",
            lw=1.1,
            clip_on=False
        )
        ax.text(x_center, y + height, f"p={p:.3g}\nq={q:.3g}", ha="center", va="bottom", fontsize=8)

    def draw_change_boxplot(self, lipid_df, lipid, groups_present):
        """Boxplot + individual observations of change scores for one lipid. Returns fig, ax."""
        fig, ax = plt.subplots(figsize=(9, 5))

        sns.boxplot(
            data=lipid_df,
            x="treatment_group",
            y="Difference",
            hue="Responder",
            order=groups_present,
            hue_order=self.responder_order,
            width=0.65,
            ax=ax
        )
        sns.stripplot(
            data=lipid_df,
            x="treatment_group",
            y="Difference",
            hue="Responder",
            order=groups_present,
            hue_order=self.responder_order,
            dodge=True,
            alpha=0.35,
            size=3,
            color="black",
            ax=ax
        )

        # Boxplot and stripplot both add legend entries; keep one per label
        handles, labels = ax.get_legend_handles_labels()
        if handles:
            unique = dict(zip(labels, handles))
            ax.legend(unique.values(), unique.keys(), title="Responder status", loc="best")

        ax.axhline(0, linestyle="--", color="grey", linewidth=1)

        ax.set_title(f"{lipid}: Change from Before to After")
        ax.set_xlabel("Treatment group")
        ax.set_ylabel("Change (After - Before)")
        ax.tick_params(axis="x", rotation=15)

        return fig, ax

    def annotate_significant_tests(self, ax, lipid_df, lipid_stats, groups_present, alpha=0.05):
        """Add p/q brackets only for comparisons with raw P_Value < alpha."""
        group_positions = {g: i for i, g in enumerate(groups_present)}

        for _, row in lipid_stats.iterrows():
            treatment = row["treatment_group"]
            p = row["P_Value"]
            q = row["q_value"]

            if treatment not in group_positions:
                continue
            if pd.isna(p) or pd.isna(q):
                continue
            if p >= alpha:
                continue

            group_data = lipid_df[lipid_df["treatment_group"] == treatment]["Difference"].dropna()
            if group_data.empty:
                continue

            y_max = group_data.max()
            y_min = group_data.min()
            span = max(y_max - y_min, abs(y_max) * 0.05, 1e-6)

            self.add_comparison_annotation(
                ax, group_positions[treatment], y_max + span * 0.15, span * 0.04, p, q
            )

        # Allow space for annotations
        ax.margins(y=0.25)

    def save_figure(self, fig, file_name, output_dir):
        """Save figure as high-resolution PNG and close it."""
        fig.tight_layout()
        output_file = os.path.join(output_dir, file_name)
        fig.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved plot: {file_name}")
        return output_file

    def safe_file_name(self, name):
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)

    def plot_change_boxplots(self, change_df, stats_df, lipid_list):
        """One change-score boxplot per lipid, responders vs non-responders per treatment group."""
        for lipid in lipid_list:
            lipid_df = change_df[change_df["Lipid"] == lipid].copy()
            if lipid_df.empty:
                continue

            groups_present = [
                g for g in self.group_order if g in lipid_df["treatment_group"].unique()
            ]

            fig, ax = self.draw_change_boxplot(lipid_df, lipid, groups_present)
            lipid_stats = stats_df[stats_df["Lipid"] == lipid]
            self.annotate_significant_tests(ax, lipid_df, lipid_stats, groups_present)

            file_name = f"{self.safe_file_name(lipid)}_change_comparison.png"
            self.save_figure(fig, file_name, self.change_output_path)

    def run(self):
        # Step 0: Load paired t-test input data
        raw_df = self.extract_csv("cleaned_paired_ttest_treatmentgroup.csv")
        print("Input data loaded.")
        print(raw_df.head())

        # Step 1: Derive responder/treatment columns and identify lipid columns
        data, lipid_list = self.prepare_data(raw_df)

        # Step 2: Individual-level change scores (After - Before)
        change_df = self.calculate_change_scores(data, lipid_list)
        self.load_csv(os.path.join("change_comparison", "individual_change_scores.csv"), change_df)
        print("Individual-level change scores calculated.")

        # Step 3: Responder vs non-responder Welch t-tests + BH FDR
        stats_df = self.run_responder_tests(change_df, lipid_list)
        self.load_csv(os.path.join("change_comparison", "responder_vs_nonresponder_change_tests.csv"), stats_df)
        print("Statistical tests completed.")

        # Step 4: Change-score boxplots with p/q annotations
        self.plot_change_boxplots(change_df, stats_df, lipid_list)

        print("\nChange-score analysis completed!")
        print(f"Plots and results saved in: {self.change_output_path}")


if __name__ == "__main__":
    ResponderAnalysis().run()
