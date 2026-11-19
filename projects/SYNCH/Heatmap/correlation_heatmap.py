import os
import re
import sys

import matplotlib.colors as mcolors
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)
from DataProcessor.ProcessorClass import ProcessorClass


class CorrelationHeatmap(ProcessorClass):
    """Heatmaps of repeated-measures lipid-clinical correlations per treatment group."""

    def __init__(self):
        super().__init__(__file__)
        self.heatmap_output_path = os.path.join(self.output_path, "correlation_heatmaps")
        os.makedirs(self.heatmap_output_path, exist_ok=True)

        self.r_threshold = 0.6
        self.treatment_order = ["Synbiotics", "Synbiotics + FMT"]

    def get_clinic_columns(self, clinic_before):
        """Clinical marker names as built in Corelation preprocessing (strip 'before_', skip 3 metadata columns)."""
        columns = clinic_before.columns.str.replace(r"^before_", "", regex=True)
        return columns[3:].tolist()

    def get_lipid_columns(self, lipid_raw):
        """Lipid names as built in Corelation preprocessing (skip first 2 columns)."""
        return lipid_raw.columns[2:].tolist()

    def build_title_mapping(self, clinic_columns, lipid_columns):
        """Map correlation title 'clinic - lipid' back to its clinical marker and lipid."""
        return {
            f"{clinic} - {lipid}": {"clinic_marker": clinic, "lipid": lipid}
            for clinic in clinic_columns
            for lipid in lipid_columns
        }

    def match_titles(self, corr_df, title_mapping):
        """Add clinic_marker and lipid columns to correlation results; warn about unmatched titles."""
        corr_df = corr_df.copy()
        corr_df["title"] = corr_df["title"].astype(str)
        corr_df["clinic_marker"] = corr_df["title"].map(
            lambda x: title_mapping.get(x, {}).get("clinic_marker")
        )
        corr_df["lipid"] = corr_df["title"].map(
            lambda x: title_mapping.get(x, {}).get("lipid")
        )

        unmatched = corr_df[corr_df["clinic_marker"].isna() | corr_df["lipid"].isna()]
        if not unmatched.empty:
            print("\nWARNING: Some correlation titles could not be matched.")
            print(unmatched["title"].head(20).to_string(index=False))

        corr_df["r"] = pd.to_numeric(corr_df["r"], errors="coerce")

        return corr_df

    def filter_strong_correlations(self, corr_df):
        """Keep matched correlations with |r| > r_threshold."""
        corr_filtered = corr_df[
            (corr_df["r"] > self.r_threshold) | (corr_df["r"] < -self.r_threshold)
        ].copy()

        return corr_filtered.dropna(subset=["clinic_marker", "lipid", "r"])

    def build_heatmap_matrix(self, df):
        """Pivot to clinical markers (rows) x lipids (columns), both sorted."""
        matrix = df.pivot(index="clinic_marker", columns="lipid", values="r")
        matrix = matrix.sort_index()
        return matrix.reindex(sorted(matrix.columns), axis=1)

    def build_annotation_matrix(self, matrix):
        """Text labels: show r only where |r| > r_threshold, otherwise empty."""
        annotation = matrix.copy().astype(object)

        for row in annotation.index:
            for col in annotation.columns:
                value = matrix.loc[row, col]
                if pd.notna(value) and abs(value) > self.r_threshold:
                    annotation.loc[row, col] = f"{value:.2f}"
                else:
                    annotation.loc[row, col] = ""

        return annotation

    def build_grey_center_cmap(self):
        """RdBu_r colormap where |r| < 0.3 is shown grey."""
        cmap_colors = plt.get_cmap("RdBu_r", 256)(np.linspace(0, 1, 256))

        # Map -0.3..+0.3 on the -1..+1 scale to colormap indices
        grey_start = int(((-0.3 + 1) / 2) * 256)
        grey_end = int(((0.3 + 1) / 2) * 256)
        cmap_colors[grey_start:grey_end] = mcolors.to_rgba("#D3D3D3")

        return mcolors.ListedColormap(cmap_colors)

    def draw_heatmap(self, matrix, title, cmap, annot, fmt):
        """Draw one correlation heatmap. Returns fig, ax."""
        fig_width = max(10, matrix.shape[1] * 0.5)
        fig_height = max(6, matrix.shape[0] * 0.5)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        sns.heatmap(
            matrix,
            cmap=cmap,
            vmin=-1,
            vmax=1,
            center=0,
            annot=annot,
            fmt=fmt,
            linewidths=0.5,
            linecolor="white",
            mask=matrix.isna(),
            cbar_kws={"label": "Repeated-measures correlation (r)"},
            ax=ax
        )

        ax.set_title(title, fontsize=14, pad=15)
        ax.set_xlabel("Lipids")
        ax.set_ylabel("Clinical markers")
        ax.tick_params(axis="x", rotation=90)
        ax.tick_params(axis="y", rotation=0)

        return fig, ax

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

    def plot_heatmaps(self, corr_df, corr_filtered):
        """Per treatment: a strong-only heatmap and a full-matrix heatmap."""
        sns.set_theme(style="white")
        grey_center_cmap = self.build_grey_center_cmap()

        for treatment in self.treatment_order:
            safe_treatment = self.safe_file_name(treatment)

            # Strong correlations only (|r| > threshold)
            strong_df = corr_filtered[corr_filtered["treatment"] == treatment]
            if not strong_df.empty:
                matrix = self.build_heatmap_matrix(strong_df)
                fig, _ = self.draw_heatmap(
                    matrix,
                    title=f"{treatment}\nStrong lipid-clinical correlations",
                    cmap="RdBu_r",
                    annot=True,
                    fmt=".2f"
                )
                self.save_figure(fig, f"{safe_treatment}_correlation_heatmap.png", self.heatmap_output_path)

            # Full matrix, numbers shown only for |r| > threshold
            full_df = corr_df[corr_df["treatment"] == treatment].dropna(
                subset=["clinic_marker", "lipid", "r"]
            )
            if full_df.empty:
                print(f"No correlation data available for {treatment}")
                continue

            full_matrix = self.build_heatmap_matrix(full_df)
            fig, _ = self.draw_heatmap(
                full_matrix,
                title=f"{treatment}\nFull correlation matrix",
                cmap=grey_center_cmap,
                annot=self.build_annotation_matrix(full_matrix),
                fmt=""
            )
            self.save_figure(fig, f"figure_all_{safe_treatment}_correlation_heatmap.png", self.heatmap_output_path)

    def run(self):
        # Step 0: Load correlation results (from Corelation module) and source data for column names
        corr_df = self.extract_csv("repeat_measures_corelation_clinic_results.csv")
        clinic_before = self.extract_csv("clinic_before.csv")
        lipid_raw = self.extract_csv("cleaned_synch_truth_treatmentgroup.csv")
        print(f"Loaded {len(corr_df)} correlation results")

        # Step 1: Split correlation titles into clinical marker and lipid
        title_mapping = self.build_title_mapping(
            self.get_clinic_columns(clinic_before),
            self.get_lipid_columns(lipid_raw)
        )
        corr_df = self.match_titles(corr_df, title_mapping)

        # Step 2: Filter strong correlations and save
        corr_filtered = self.filter_strong_correlations(corr_df)
        filtered_file = self.load_csv(
            os.path.join("correlation_heatmaps", "strong_correlations.csv"), corr_filtered
        )
        print(f"\nTotal correlations: {len(corr_df)}")
        print(f"Strong correlations: {len(corr_filtered)}")
        print(f"Filtered results saved: {filtered_file}")

        # Step 3: Heatmaps per treatment
        self.plot_heatmaps(corr_df, corr_filtered)

        print("\nCorrelation heatmaps completed!")
        print(f"Results saved in: {self.heatmap_output_path}")


if __name__ == "__main__":
    CorrelationHeatmap().run()
