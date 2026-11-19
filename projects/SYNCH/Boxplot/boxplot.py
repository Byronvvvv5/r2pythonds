
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re

# ============================================================
# 1. Define folder paths
# ============================================================

# Folder where this script.py is located
base_dir = Path(__file__).resolve().parent

# Input and output folders
input_dir = base_dir / "input"
output_dir = base_dir / "output"

# Create output folder automatically if it does not exist
output_dir.mkdir(parents=True, exist_ok=True)

# Input files
data_file = input_dir / "cleaned_synch_truth_treatmentgroup.csv"
test_file = input_dir / "paired_t_test_results_sig_withoutresponder.csv"


# ============================================================
# 2. Read datasets
# ============================================================

data = pd.read_csv(data_file)
tests = pd.read_csv(test_file)

# Extract lipid names from paired t-test results
lipid_list = tests["Lipid"].dropna().unique().tolist()

group_order = ["placebo", "Synbiotics", "Synbiotics + FMT"]
time_order = ["Before", "After"]


# ============================================================
# 3. Function to add P-value annotation
# ============================================================

def add_p_bracket(ax, x_center, y, h, p):

    ax.plot(
        [x_center - 0.18, x_center - 0.18,
         x_center + 0.18, x_center + 0.18],
        [y, y + h, y + h, y],
        lw=1.1,
        c="black",
        clip_on=False
    )

    ax.text(
        x_center,
        y + h,
        f"p = {p:.3g}",
        ha="center",
        va="bottom",
        fontsize=9
    )


# ============================================================
# 4. Draw one boxplot for each lipid
# ============================================================

for lipid in lipid_list:

    # Check whether lipid exists in dataset 1
    if lipid not in data.columns:
        print(f"Skipping {lipid}: column not found")
        continue

    # Only include treatment groups present in the dataset
    groups_present = [
        g for g in group_order
        if g in data["treatment_group"].unique()
    ]

    fig, ax = plt.subplots(figsize=(8, 5))

    # Boxplots: Before and After within each treatment group
    sns.boxplot(
        data=data,
        x="treatment_group",
        y=lipid,
        hue="Time",
        order=groups_present,
        hue_order=time_order,
        width=0.65,
        ax=ax
    )

    # Overlay individual observations
    sns.stripplot(
        data=data,
        x="treatment_group",
        y=lipid,
        hue="Time",
        order=groups_present,
        hue_order=time_order,
        dodge=True,
        alpha=0.35,
        size=3,
        ax=ax,
        color="black"
    )

    # Remove duplicate legend entries
    handles, labels = ax.get_legend_handles_labels()

    if handles:
        unique = dict(zip(labels, handles))
        ax.legend(
            unique.values(),
            unique.keys(),
            title="Time",
            loc="best"
        )

    # Labels and title
    ax.set_title(lipid)
    ax.set_xlabel("Treatment group")
    ax.set_ylabel(lipid)
    ax.tick_params(axis="x", rotation=15)

    # ========================================================
    # Add P-values for this lipid and treatment group
    # ========================================================

    lipid_tests = tests[tests["Lipid"] == lipid]

    group_positions = {
        g: i for i, g in enumerate(groups_present)
    }

    for _, row in lipid_tests.iterrows():

        group = row["Group"]
        p = row["P_Value"]

        # Skip if group or P-value is unavailable
        if group not in group_positions or pd.isna(p):
            continue

        group_data = data.loc[
            data["treatment_group"] == group,
            lipid
        ].dropna()

        if group_data.empty:
            continue

        y_max = group_data.max()
        y_min = group_data.min()

        span = max(
            y_max - y_min,
            abs(y_max) * 0.05,
            1e-6
        )

        y = y_max + span * 0.12

        add_p_bracket(
            ax,
            group_positions[group],
            y,
            span * 0.04,
            p
        )

    # Allow space for annotations
    ax.margins(y=0.18)

    fig.tight_layout()

    # ========================================================
    # Save figure into output folder
    # ========================================================

    safe_name = re.sub(
        r"[^A-Za-z0-9_.-]+",
        "_",
        lipid
    )

    output_file = output_dir / f"{safe_name}.png"

    fig.savefig(
        output_file,
        dpi=300,
        bbox_inches="tight"
    )

    plt.close(fig)

    print(f"Saved: {output_file.name}")


# ============================================================
# 5. Finished
# ============================================================

print("\nAll plots have been generated successfully!")
print(f"Plots saved in: {output_dir}")


# ============================================================
# 6. RESPONDER / NON-RESPONDER ANALYSIS
# ============================================================

print("\nStarting responder/non-responder analysis...")

# ---- Define input files and output folder ----

responder_data_file = input_dir / "cleaned_paired_ttest_treatmentgroup.csv"
responder_test_file = input_dir / "paired_t_test_results_sig.csv"

responder_output_dir = output_dir / "responder"
responder_output_dir.mkdir(parents=True, exist_ok=True)


# ---- Read datasets ----

responder_data = pd.read_csv(responder_data_file)
responder_tests = pd.read_csv(responder_test_file)


# ---- Extract lipid names from paired test results ----

responder_lipid_list = (
    responder_tests["Lipid"]
    .dropna()
    .unique()
    .tolist()
)


# ---- Define treatment group and time order ----

group_order = ["placebo", "Synbiotics", "Synbiotics + FMT"]
time_order = ["Before", "After"]

# Both responder statuses
responder_statuses = {
    "Yes": "Responder",
    "No": "Non-responder"
}


# ---- Draw plots for each lipid and responder status ----

for lipid in responder_lipid_list:

    if lipid not in responder_data.columns:
        print(f"Skipping {lipid}: column not found")
        continue

    # --------------------------------------------------------
    # Loop over Responder and Non-responder
    # --------------------------------------------------------

    for status_prefix, status_label in responder_statuses.items():

        # Select data for this status only
        status_data = responder_data[
            responder_data["Group"]
            .astype(str)
            .str.startswith(f"{status_prefix}-", na=False)
        ].copy()

        if status_data.empty:
            print(f"Skipping {lipid} ({status_label}): no data")
            continue

        # Determine treatment groups present
        groups_present = [
            g for g in group_order
            if g in status_data["treatment_group"].unique()
        ]

        if not groups_present:
            continue

        # ----------------------------------------------------
        # Create figure
        # ----------------------------------------------------

        fig, ax = plt.subplots(figsize=(8, 5))

        # Boxplots
        sns.boxplot(
            data=status_data,
            x="treatment_group",
            y=lipid,
            hue="Time",
            order=groups_present,
            hue_order=time_order,
            width=0.65,
            ax=ax
        )

        # Individual observations
        sns.stripplot(
            data=status_data,
            x="treatment_group",
            y=lipid,
            hue="Time",
            order=groups_present,
            hue_order=time_order,
            dodge=True,
            alpha=0.35,
            size=3,
            color="black",
            ax=ax
        )

        # ----------------------------------------------------
        # Remove duplicate legend entries
        # ----------------------------------------------------

        handles, labels = ax.get_legend_handles_labels()

        if handles:
            unique = dict(zip(labels, handles))
            ax.legend(
                unique.values(),
                unique.keys(),
                title="Time",
                loc="best"
            )

        # ----------------------------------------------------
        # Labels and title
        # ----------------------------------------------------

        ax.set_title(f"{lipid} ({status_label})")
        ax.set_xlabel("Treatment group")
        ax.set_ylabel(lipid)
        ax.tick_params(axis="x", rotation=15)

        # ----------------------------------------------------
        # Add P-values
        # ----------------------------------------------------

        lipid_tests = responder_tests[
            responder_tests["Lipid"] == lipid
        ]

        group_positions = {
            g: i for i, g in enumerate(groups_present)
        }

        for _, row in lipid_tests.iterrows():

            test_group = str(row["Group"])
            p = row["P_Value"]

            if pd.isna(p):
                continue

            # Only use test results matching this status
            if not test_group.startswith(f"{status_prefix}-"):
                continue

            # Convert test group to plotting group
            # Example: Yes-Synbiotics -> Synbiotics
            plotting_group = test_group.replace(
                f"{status_prefix}-",
                "",
                1
            )

            if plotting_group not in group_positions:
                continue

            # Data for the corresponding treatment group
            group_data = status_data.loc[
                status_data["treatment_group"] == plotting_group,
                lipid
            ].dropna()

            if group_data.empty:
                continue

            y_max = group_data.max()
            y_min = group_data.min()

            span = max(
                y_max - y_min,
                abs(y_max) * 0.05,
                1e-6
            )

            y = y_max + span * 0.12

            # Add p-value bracket
            add_p_bracket(
                ax,
                group_positions[plotting_group],
                y,
                span * 0.04,
                p
            )

        # ----------------------------------------------------
        # Save plot
        # ----------------------------------------------------

        ax.margins(y=0.18)
        fig.tight_layout()

        safe_name = re.sub(
            r"[^A-Za-z0-9_.-]+",
            "_",
            lipid
        )

        output_file = responder_output_dir / (
            f"{safe_name}_{status_label.replace(' ', '_')}.png"
        )

        fig.savefig(
            output_file,
            dpi=300,
            bbox_inches="tight"
        )

        plt.close(fig)

        print(f"Saved: {output_file.name}")


print("\nResponder/non-responder plots completed!")
print(f"Plots saved in: {responder_output_dir}")