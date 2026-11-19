import os
import re
import sys

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from DataProcessor.ProcessorClass import ProcessorClass


class Boxplot(ProcessorClass):
    """Boxplots (Before/After per treatment group) for lipids with paired t-test p-values."""

    def __init__(self):
        super().__init__(__file__)
        self.responder_output_path = os.path.join(self.output_path, "responder")
        os.makedirs(self.responder_output_path, exist_ok=True)

        self.group_order = ["placebo", "Synbiotics", "Synbiotics + FMT"]
        self.time_order = ["Before", "After"]
        self.responder_statuses = {
            "Yes": "Responder",
            "No": "Non-responder"
        }

    def get_lipid_list(self, tests):
        """Extract unique lipid names from paired t-test results."""
        return tests["Lipid"].dropna().unique().tolist()

    def get_groups_present(self, df):
        """Treatment groups in plotting order, limited to those present in the data."""
        return [g for g in self.group_order if g in df["treatment_group"].unique()]

    def filter_responder_status(self, df, status_prefix):
        """Keep rows whose Group starts with e.g. 'Yes-' or 'No-'."""
        return df[
            df["Group"].astype(str).str.startswith(f"{status_prefix}-", na=False)
        ].copy()

    def add_p_bracket(self, ax, x_center, y, h, p):
        """Draw a bracket with the p-value above one treatment group."""
        ax.plot(
            [x_center - 0.18, x_center - 0.18, x_center + 0.18, x_center + 0.18],
            [y, y + h, y + h, y],
            lw=1.1,
            c="black",
            clip_on=False
        )
        ax.text(x_center, y + h, f"p = {p:.3g}", ha="center", va="bottom", fontsize=9)

    def draw_boxplot(self, df, lipid, groups_present, title):
        """Draw boxplot + individual observations for one lipid. Returns fig, ax."""
        fig, ax = plt.subplots(figsize=(8, 5))

        sns.boxplot(
            data=df,
            x="treatment_group",
            y=lipid,
            hue="Time",
            order=groups_present,
            hue_order=self.time_order,
            width=0.65,
            ax=ax
        )
        sns.stripplot(
            data=df,
            x="treatment_group",
            y=lipid,
            hue="Time",
            order=groups_present,
            hue_order=self.time_order,
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
            ax.legend(unique.values(), unique.keys(), title="Time", loc="best")

        ax.set_title(title)
        ax.set_xlabel("Treatment group")
        ax.set_ylabel(lipid)
        ax.tick_params(axis="x", rotation=15)

        return fig, ax

    def annotate_p_values(self, ax, df, lipid, lipid_tests, groups_present, status_prefix=None):
        """
        Add p-value brackets for each tested treatment group.

        If status_prefix is given (e.g. 'Yes'), only tests with Group 'Yes-<treatment>'
        are used and the prefix is stripped to match the plotted treatment group.
        """
        group_positions = {g: i for i, g in enumerate(groups_present)}

        for _, row in lipid_tests.iterrows():
            group = row["Group"]
            p = row["P_Value"]

            if pd.isna(p):
                continue

            if status_prefix is not None:
                group = str(group)
                if not group.startswith(f"{status_prefix}-"):
                    continue
                group = group.replace(f"{status_prefix}-", "", 1)

            if group not in group_positions:
                continue

            group_data = df.loc[df["treatment_group"] == group, lipid].dropna()
            if group_data.empty:
                continue

            y_max = group_data.max()
            y_min = group_data.min()
            span = max(y_max - y_min, abs(y_max) * 0.05, 1e-6)

            self.add_p_bracket(ax, group_positions[group], y_max + span * 0.12, span * 0.04, p)

        # Allow space for annotations
        ax.margins(y=0.18)

    def save_figure(self, fig, file_name, output_dir):
        """Save figure as high-resolution PNG and close it."""
        fig.tight_layout()
        output_file = os.path.join(output_dir, file_name)
        fig.savefig(output_file, dpi=300, bbox_inches="tight")
        plt.close(fig)
        print(f"Saved: {file_name}")
        return output_file

    def safe_file_name(self, name):
        return re.sub(r"[^A-Za-z0-9_.-]+", "_", name)

    def plot_treatment_boxplots(self, data, tests):
        """One boxplot per significant lipid, all subjects."""
        groups_present = self.get_groups_present(data)

        for lipid in self.get_lipid_list(tests):
            if lipid not in data.columns:
                print(f"Skipping {lipid}: column not found")
                continue

            fig, ax = self.draw_boxplot(data, lipid, groups_present, title=lipid)
            lipid_tests = tests[tests["Lipid"] == lipid]
            self.annotate_p_values(ax, data, lipid, lipid_tests, groups_present)

            self.save_figure(fig, f"{self.safe_file_name(lipid)}.png", self.output_path)

    def plot_responder_boxplots(self, data, tests):
        """One boxplot per significant lipid and responder status."""
        for lipid in self.get_lipid_list(tests):
            if lipid not in data.columns:
                print(f"Skipping {lipid}: column not found")
                continue

            lipid_tests = tests[tests["Lipid"] == lipid]

            for status_prefix, status_label in self.responder_statuses.items():
                status_data = self.filter_responder_status(data, status_prefix)
                if status_data.empty:
                    print(f"Skipping {lipid} ({status_label}): no data")
                    continue

                groups_present = self.get_groups_present(status_data)
                if not groups_present:
                    continue

                fig, ax = self.draw_boxplot(
                    status_data, lipid, groups_present, title=f"{lipid} ({status_label})"
                )
                self.annotate_p_values(
                    ax, status_data, lipid, lipid_tests, groups_present, status_prefix=status_prefix
                )

                file_name = f"{self.safe_file_name(lipid)}_{status_label.replace(' ', '_')}.png"
                self.save_figure(fig, file_name, self.responder_output_path)

    def run(self):
        # Step 1: Boxplots for all subjects, with paired t-test p-values
        data = self.extract_csv("cleaned_synch_truth_treatmentgroup.csv")
        tests = self.extract_csv("paired_t_test_results_sig_withoutresponder.csv")
        self.plot_treatment_boxplots(data, tests)
        print(f"\nAll plots have been generated successfully!\nPlots saved in: {self.output_path}")

        # Step 2: Boxplots split by responder / non-responder
        print("\nStarting responder/non-responder analysis...")
        responder_data = self.extract_csv("cleaned_paired_ttest_treatmentgroup.csv")
        responder_tests = self.extract_csv("paired_t_test_results_sig.csv")
        self.plot_responder_boxplots(responder_data, responder_tests)
        print(f"\nResponder/non-responder plots completed!\nPlots saved in: {self.responder_output_path}")


if __name__ == "__main__":
    Boxplot().run()
