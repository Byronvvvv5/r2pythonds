
# ============================================================
# correlation_heatmap.py
# ============================================================

import re
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

# ============================================================
# 1. DEFINE PATHS
# ============================================================

base_dir = Path(__file__).resolve().parent

input_dir = base_dir / "input"
output_dir = base_dir / "output"

correlation_file = (
    output_dir / "repeat_measures_corelation_clinic_results.csv"
)

clinic_before_file = input_dir / "clinic_before.csv"
lipid_file = input_dir / "cleaned_synch_truth_treatmentgroup.csv"

heatmap_output_dir = output_dir / "correlation_heatmaps"
heatmap_output_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. SETTINGS
# ============================================================

r_threshold = 0.6

treatment_order = [
    "Synbiotics",
    "Synbiotics + FMT"
]


# ============================================================
# 3. READ DATA
# ============================================================

corr_df = pd.read_csv(correlation_file)

clinic_before = pd.read_csv(clinic_before_file)
lipid_raw = pd.read_csv(lipid_file)

print(f"Loaded {len(corr_df)} correlation results")


# ============================================================
# 4. RECONSTRUCT CLINICAL MARKER AND LIPID COLUMN NAMES
#    BASED ON ORIGINAL PREPROCESSING
# ============================================================

# ---- Clinical markers ----

clinic_before.columns = clinic_before.columns.str.replace(
    r"^before_", "",
    regex=True
)

# Original preprocessing uses the first 3 columns as metadata
clinic_columns = clinic_before.columns[3:].tolist()


# ---- Lipids ----

# Original preprocessing:
# df_lipids = df_lipids.iloc[:, 2:]
# Then treatment_group and Time are moved to the front.
#
# Therefore the lipid feature columns are those remaining
# after the metadata columns in the transformed dataframe.

lipid_columns = lipid_raw.columns[2:].tolist()


# ============================================================
# 5. MATCH CORRELATION TITLE TO CLINICAL MARKER AND LIPID
# ============================================================

# Original title format:
# f"{col_1} - {col_2}"
#
# col_1 = clinical marker
# col_2 = lipid

title_mapping = {}

for clinic in clinic_columns:
    for lipid in lipid_columns:

        title = f"{clinic} - {lipid}"

        title_mapping[title] = {
            "clinic_marker": clinic,
            "lipid": lipid
        }


# ---- Match title ----

corr_df["title"] = corr_df["title"].astype(str)

corr_df["clinic_marker"] = corr_df["title"].map(
    lambda x: title_mapping.get(x, {}).get("clinic_marker")
)

corr_df["lipid"] = corr_df["title"].map(
    lambda x: title_mapping.get(x, {}).get("lipid")
)


# ---- Check unmatched titles ----

unmatched = corr_df[
    corr_df["clinic_marker"].isna()
    | corr_df["lipid"].isna()
]

if not unmatched.empty:

    print("\nWARNING: Some correlation titles could not be matched.")

    print(
        unmatched["title"].head(20).to_string(index=False)
    )


# ============================================================
# 6. FILTER STRONG CORRELATIONS
# ============================================================

corr_df["r"] = pd.to_numeric(
    corr_df["r"],
    errors="coerce"
)

corr_filtered = corr_df[
    (corr_df["r"] > r_threshold)
    | (corr_df["r"] < -r_threshold)
].copy()


# Remove unmatched entries
corr_filtered = corr_filtered.dropna(
    subset=["clinic_marker", "lipid", "r"]
)


# ============================================================
# 7. SAVE FILTERED CORRELATION RESULTS
# ============================================================

filtered_file = (
    heatmap_output_dir / "strong_correlations.csv"
)

corr_filtered.to_csv(
    filtered_file,
    index=False
)

print(f"\nTotal correlations: {len(corr_df)}")
print(f"Strong correlations: {len(corr_filtered)}")
print(f"Filtered results saved: {filtered_file}")


# ============================================================
# 8. DRAW HEATMAPS
# ============================================================

import matplotlib.colors as mcolors

sns.set_theme(style="white")


# ---- Create a custom colormap ----
# Correlations with |r| < 0.3 will appear grey.

base_cmap = plt.get_cmap("RdBu_r", 256)
cmap_colors = base_cmap(np.linspace(0, 1, 256))

# Values from -0.3 to +0.3 correspond approximately
# to indices 89 to 166 in the -1 to +1 scale.
grey_start = int(((-0.3 + 1) / 2) * 256)
grey_end = int(((0.3 + 1) / 2) * 256)

cmap_colors[grey_start:grey_end] = mcolors.to_rgba("#D3D3D3")

custom_cmap = mcolors.ListedColormap(cmap_colors)


for treatment in treatment_order:

    # ========================================================
    # 8A. ORIGINAL THRESHOLD HEATMAP
    #     Only |r| > 0.6
    # ========================================================

    treatment_df = corr_filtered[
        corr_filtered["treatment"] == treatment
    ].copy()

    if not treatment_df.empty:

        heatmap_data = treatment_df.pivot(
            index="clinic_marker",
            columns="lipid",
            values="r"
        )

        heatmap_data = heatmap_data.sort_index()

        heatmap_data = heatmap_data.reindex(
            sorted(heatmap_data.columns),
            axis=1
        )

        fig_width = max(
            10,
            heatmap_data.shape[1] * 0.5
        )

        fig_height = max(
            6,
            heatmap_data.shape[0] * 0.5
        )

        fig, ax = plt.subplots(
            figsize=(fig_width, fig_height)
        )

        sns.heatmap(
            heatmap_data,
            cmap="RdBu_r",
            vmin=-1,
            vmax=1,
            center=0,
            annot=True,
            fmt=".2f",
            linewidths=0.5,
            linecolor="white",
            mask=heatmap_data.isna(),
            cbar_kws={
                "label": "Repeated-measures correlation (r)"
            },
            ax=ax
        )

        ax.set_title(
            f"{treatment}\nStrong lipid-clinical correlations",
            fontsize=14,
            pad=15
        )

        ax.set_xlabel("Lipids")
        ax.set_ylabel("Clinical markers")

        ax.tick_params(axis="x", rotation=90)
        ax.tick_params(axis="y", rotation=0)

        fig.tight_layout()

        safe_treatment = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "_",
            treatment
        )

        output_file = (
            heatmap_output_dir
            / f"{safe_treatment}_correlation_heatmap.png"
        )

        fig.savefig(
            output_file,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close(fig)

        print(f"Saved: {output_file.name}")


    # ========================================================
    # 8B. NEW FULL CORRELATION HEATMAP
    #     All correlation values
    # ========================================================

    full_treatment_df = corr_df[
        corr_df["treatment"] == treatment
    ].copy()

    full_treatment_df = full_treatment_df.dropna(
        subset=["clinic_marker", "lipid", "r"]
    )

    if full_treatment_df.empty:

        print(
            f"No correlation data available for {treatment}"
        )

        continue


    # --------------------------------------------------------
    # Create full correlation matrix
    # --------------------------------------------------------

    full_heatmap_data = full_treatment_df.pivot(
        index="clinic_marker",
        columns="lipid",
        values="r"
    )

    full_heatmap_data = full_heatmap_data.sort_index()

    full_heatmap_data = full_heatmap_data.reindex(
        sorted(full_heatmap_data.columns),
        axis=1
    )


    # --------------------------------------------------------
    # Annotation matrix:
    # Only show numbers where |r| > 0.6
    # --------------------------------------------------------

    annotation_data = full_heatmap_data.copy().astype(object)

    for row in annotation_data.index:

        for col in annotation_data.columns:

            value = full_heatmap_data.loc[row, col]

            if pd.isna(value):

                annotation_data.loc[row, col] = ""

            elif abs(value) > 0.6:

                annotation_data.loc[row, col] = f"{value:.2f}"

            else:

                annotation_data.loc[row, col] = ""


    # --------------------------------------------------------
    # Figure size
    # --------------------------------------------------------

    fig_width = max(
        10,
        full_heatmap_data.shape[1] * 0.5
    )

    fig_height = max(
        6,
        full_heatmap_data.shape[0] * 0.5
    )

    fig, ax = plt.subplots(
        figsize=(fig_width, fig_height)
    )


    # --------------------------------------------------------
    # Full heatmap
    # --------------------------------------------------------

    sns.heatmap(
        full_heatmap_data,

        cmap=custom_cmap,
        vmin=-1,
        vmax=1,
        center=0,

        annot=annotation_data,
        fmt="",

        linewidths=0.5,
        linecolor="white",

        mask=full_heatmap_data.isna(),

        cbar_kws={
            "label": "Repeated-measures correlation (r)"
        },

        ax=ax
    )


    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    ax.set_title(
        f"{treatment}\nFull correlation matrix",
        fontsize=14,
        pad=15
    )

    ax.set_xlabel("Lipids")
    ax.set_ylabel("Clinical markers")

    ax.tick_params(
        axis="x",
        rotation=90
    )

    ax.tick_params(
        axis="y",
        rotation=0
    )


    fig.tight_layout()


    # --------------------------------------------------------
    # Save new figure
    # --------------------------------------------------------

    safe_treatment = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        treatment
    )

    output_file = (
        heatmap_output_dir
        / f"figure_all_{safe_treatment}_correlation_heatmap.png"
    )

    fig.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {output_file.name}")


# ============================================================
# 9. FINISH
# ============================================================

print("\nCorrelation heatmaps completed!")

print(
    f"Results saved in: {heatmap_output_dir}"
)