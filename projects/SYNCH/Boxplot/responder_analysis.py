import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from pathlib import Path
import re
from scipy.stats import ttest_ind
from statsmodels.stats.multitest import multipletests


# ============================================================
# 1. Define folders
# ============================================================

base_dir = Path(__file__).resolve().parent

input_dir = base_dir / "input"
output_dir = base_dir / "output" / "change_comparison"

output_dir.mkdir(parents=True, exist_ok=True)


# ============================================================
# 2. Read input data
# ============================================================

input_file = input_dir / "cleaned_paired_ttest_treatmentgroup.csv"

data = pd.read_csv(input_file)

print("Input data loaded.")
print(data.head())


# ============================================================
# 3. Identify responder status and treatment group
# ============================================================

# This script supports either:
#   A. Separate Responder and treatment_group columns
#   B. A combined Group column such as Yes-Synbiotics

if "Responder" not in data.columns:

    if "Group" not in data.columns:
        raise ValueError(
            "The dataset must contain either a Responder column "
            "or a Group column."
        )

    # Derive responder status from the beginning of Group
    data["Responder"] = (
        data["Group"]
        .astype(str)
        .str.extract(r"^(Yes|No)", expand=False)
    )

    data["Responder"] = data["Responder"].map({
        "Yes": "Responder",
        "No": "Non-responder"
    })


if "treatment_group" not in data.columns:

    if "Group" not in data.columns:
        raise ValueError(
            "The dataset must contain a treatment_group column "
            "or a combined Group column."
        )

    # Remove the Yes-/No- prefix to obtain the treatment group
    data["treatment_group"] = (
        data["Group"]
        .astype(str)
        .str.replace(r"^(Yes|No)-", "", regex=True)
    )


# Standardize responder labels if needed
data["Responder"] = data["Responder"].replace({
    "Yes": "Responder",
    "No": "Non-responder",
    "yes": "Responder",
    "no": "Non-responder"
})


# ============================================================
# 4. Define metadata and lipid columns
# ============================================================

metadata_cols = [
    "ID",
    "Time",
    "Responder",
    "treatment_group",
    "Group"
]

metadata_cols = [
    col for col in metadata_cols
    if col in data.columns
]

lipid_list = [
    col for col in data.columns
    if col not in metadata_cols
]

print(f"Number of lipid columns: {len(lipid_list)}")


# Convert lipid measurements to numeric
for lipid in lipid_list:
    data[lipid] = pd.to_numeric(data[lipid], errors="coerce")


# ============================================================
# 5. Calculate individual-level change scores
#    Change = After - Before
# ============================================================

change_results = []

for lipid in lipid_list:

    working_df = data[
        ["ID", "Responder", "treatment_group", "Time", lipid]
    ].copy()

    working_df = working_df.dropna(
        subset=["ID", "Responder", "treatment_group", "Time", lipid]
    )

    # Reshape to one row per participant
    paired_df = working_df.pivot(
        index=["ID", "Responder", "treatment_group"],
        columns="Time",
        values=lipid
    )

    # Ensure both timepoints exist
    if not {"Before", "After"}.issubset(paired_df.columns):
        continue

    paired_df = paired_df.dropna(
        subset=["Before", "After"]
    )

    # Calculate change score
    paired_df["Difference"] = (
        paired_df["After"] - paired_df["Before"]
    )

    paired_df = paired_df.reset_index()

    paired_df["Lipid"] = lipid

    change_results.append(paired_df)


# Combine all lipid-specific change scores
if not change_results:
    raise ValueError(
        "No paired data could be generated. Check ID and Time columns."
    )

change_df = pd.concat(
    change_results,
    ignore_index=True
)


# Save individual-level change scores
change_df.to_csv(
    output_dir / "individual_change_scores.csv",
    index=False
)

print("Individual-level change scores calculated.")


# ============================================================
# 6. Compare responders vs non-responders
#    Within each treatment group and for each lipid
# ============================================================

stat_results = []

for lipid in lipid_list:

    lipid_df = change_df[
        change_df["Lipid"] == lipid
    ]

    for treatment in lipid_df["treatment_group"].dropna().unique():

        group_df = lipid_df[
            lipid_df["treatment_group"] == treatment
        ]

        responder_values = group_df.loc[
            group_df["Responder"] == "Responder",
            "Difference"
        ].dropna()

        nonresponder_values = group_df.loc[
            group_df["Responder"] == "Non-responder",
            "Difference"
        ].dropna()

        n_responder = len(responder_values)
        n_nonresponder = len(nonresponder_values)

        # Welch's independent-samples t-test
        if n_responder >= 2 and n_nonresponder >= 2:

            test_result = ttest_ind(
                responder_values,
                nonresponder_values,
                equal_var=False
            )

            t_statistic = test_result.statistic
            p_value = test_result.pvalue

        else:

            t_statistic = np.nan
            p_value = np.nan

        mean_responder = (
            responder_values.mean()
            if n_responder > 0
            else np.nan
        )

        mean_nonresponder = (
            nonresponder_values.mean()
            if n_nonresponder > 0
            else np.nan
        )

        stat_results.append({
            "Lipid": lipid,
            "treatment_group": treatment,
            "N_Responder": n_responder,
            "N_Non_responder": n_nonresponder,
            "Mean_Change_Responder": mean_responder,
            "Mean_Change_Non_responder": mean_nonresponder,
            "Mean_Difference_between_groups": (
                mean_responder - mean_nonresponder
            ),
            "T_Statistic": t_statistic,
            "P_Value": p_value
        })


stats_df = pd.DataFrame(stat_results)


# ============================================================
# 7. Multiple-testing correction
#    BH FDR across all lipid-treatment comparisons
# ============================================================

stats_df["q_value"] = np.nan

valid_p = stats_df["P_Value"].notna()

if valid_p.any():

    stats_df.loc[valid_p, "q_value"] = multipletests(
        stats_df.loc[valid_p, "P_Value"],
        method="fdr_bh"
    )[1]


# Save statistical results
stats_df.to_csv(
    output_dir / "responder_vs_nonresponder_change_tests.csv",
    index=False
)

print("Statistical tests completed.")


# ============================================================
# 8. Plotting function
# ============================================================

def add_comparison_annotation(ax, x_center, y, height, p, q):

    ax.plot(
        [x_center - 0.18, x_center - 0.18,
         x_center + 0.18, x_center + 0.18],
        [y, y + height, y + height, y],
        color="black",
        lw=1.1,
        clip_on=False
    )

    annotation = f"p={p:.3g}\nq={q:.3g}"

    ax.text(
        x_center,
        y + height,
        annotation,
        ha="center",
        va="bottom",
        fontsize=8
    )


# ============================================================
# 9. Draw one plot per lipid
# ============================================================

group_order = [
    "placebo",
    "Synbiotics",
    "Synbiotics + FMT"
]

responder_order = [
    "Non-responder",
    "Responder"
]


for lipid in lipid_list:

    lipid_df = change_df[
        change_df["Lipid"] == lipid
    ].copy()

    if lipid_df.empty:
        continue

    groups_present = [
        g for g in group_order
        if g in lipid_df["treatment_group"].unique()
    ]

    fig, ax = plt.subplots(figsize=(9, 5))

    # Boxplots of individual change scores
    sns.boxplot(
        data=lipid_df,
        x="treatment_group",
        y="Difference",
        hue="Responder",
        order=groups_present,
        hue_order=responder_order,
        width=0.65,
        ax=ax
    )

    # Overlay individual observations
    sns.stripplot(
        data=lipid_df,
        x="treatment_group",
        y="Difference",
        hue="Responder",
        order=groups_present,
        hue_order=responder_order,
        dodge=True,
        alpha=0.35,
        size=3,
        color="black",
        ax=ax
    )

    # Remove duplicate legend entries
    handles, labels = ax.get_legend_handles_labels()

    if handles:
        unique = dict(zip(labels, handles))

        ax.legend(
            unique.values(),
            unique.keys(),
            title="Responder status",
            loc="best"
        )

    # Zero reference line
    ax.axhline(
        0,
        linestyle="--",
        color="grey",
        linewidth=1
    )

    ax.set_title(f"{lipid}: Change from Before to After")
    ax.set_xlabel("Treatment group")
    ax.set_ylabel("Change (After - Before)")
    ax.tick_params(axis="x", rotation=15)


    # --------------------------------------------------------
    # Add P-values and q-values
    # Only annotate comparisons with raw P_Value < 0.05
    # --------------------------------------------------------

    lipid_stats = stats_df[
        stats_df["Lipid"] == lipid
    ]

    group_positions = {
        g: i for i, g in enumerate(groups_present)
    }

    for _, row in lipid_stats.iterrows():

        treatment = row["treatment_group"]
        p = row["P_Value"]
        q = row["q_value"]

        if treatment not in group_positions:
            continue

        if pd.isna(p) or pd.isna(q):
            continue

        # Only show annotation if raw p-value < 0.05
        if p >= 0.05:
            continue

        group_data = lipid_df[
            lipid_df["treatment_group"] == treatment
        ]["Difference"].dropna()

        if group_data.empty:
            continue

        y_max = group_data.max()
        y_min = group_data.min()

        span = max(
            y_max - y_min,
            abs(y_max) * 0.05,
            1e-6
        )

        y = y_max + span * 0.15

        add_comparison_annotation(
            ax,
            group_positions[treatment],
            y,
            span * 0.04,
            p,
            q
        )

    ax.margins(y=0.25)

    fig.tight_layout()
    
    # --------------------------------------------------------
    # Save plot
    # --------------------------------------------------------

    safe_name = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        lipid
    )

    output_file = output_dir / f"{safe_name}_change_comparison.png"

    fig.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved plot: {output_file.name}")


# ============================================================
# 10. Finished
# ============================================================

print("\nChange-score analysis completed!")
print(f"Plots and results saved in: {output_dir}")