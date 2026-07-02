import os
import sys
from pathlib import Path
import math

import pandas as pd
import matplotlib.pyplot as plt

# This tells Python where the root directory of your project is
basedir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(basedir)


def Migration_line_plots(df_long: pd.DataFrame, output_dir: str = os.path.join(os.path.dirname(__file__), 'output')) -> pd.DataFrame:
    df = df_long.copy()

    # Step 1: create the plotting group, same idea as case_when in R
    conditions = [
        (df["cell"] == "HCC1143") & (df["group"] == "Control"),
        (df["cell"] == "HCC1143") & (df["group"] == "Migration"),
        (df["cell"] == "HCC38") & (df["group"] == "Control"),
        (df["cell"] == "HCC38") & (df["group"] == "Migration"),
        (df["cell"] == "media") | (df["group"] == "media"),
    ]
    labels = [
        "1143control",
        "1143migration",
        "38control",
        "38migration",
        "media",
    ]

    df["line_group"] = pd.Series(pd.NA, index=df.index)
    for condition, label in zip(conditions, labels):
        df.loc[condition, "line_group"] = label

    # Step 2: force time ordering
    time_order = [0, 12, 18, 22]
    df["time"] = pd.Categorical(df["time"], categories=time_order, ordered=True)

    # Step 3: summarize for plotting
    plot_df = (
        df.groupby(["compound", "time", "line_group"], dropna=False)["value"]
        .agg(
            mean_value="mean",
            sd_value=lambda x: x.std(ddof=1),
            se_value=lambda x: x.std(ddof=1) / math.sqrt(x.notna().sum()) if x.notna().sum() > 0 else float("nan"),
        )
        .reset_index()
    )

    # Step 4: convert time back to numeric for plotting
    plot_df["time"] = plot_df["time"].astype(float)

    # Step 5: make one plot per compound
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    print(f"Intotal compounds to plot: {plot_df['compound'].nunique()}")
    for compound, df_sub in plot_df.groupby("compound"):
        print(f"Start plotting compound: {compound}, data shape: {df_sub.shape}, save to: {output_path / f'all_{compound}.png'} ")
        fig, ax = plt.subplots(figsize=(6, 4.5))

        for line_group, group_data in df_sub.groupby("line_group"):
            if pd.isna(line_group):
                continue

            group_data = group_data.sort_values("time")

            ax.plot(
                group_data["time"],
                group_data["mean_value"],
                marker="o",
                linewidth=1.0,
                label=line_group,
            )

        ax.set_title(compound)
        ax.set_xlabel("Time")
        ax.set_ylabel("Mean value")
        ax.set_xticks([0, 12, 18, 22])
        ax.set_xlim(0, 22)
        ax.legend(
            title="Condition",
            loc="lower left",
            bbox_to_anchor=(1.02, 0.5),
            borderaxespad=0,
        )        
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        fig.subplots_adjust(right=0.78)

        safe_name = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(compound))
        fig.savefig(output_path / f"all_{safe_name}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    return plot_df

def Migration_box_plots(df_long: pd.DataFrame, output_dir: str = os.path.join(os.path.dirname(__file__), 'output')) -> pd.DataFrame:
    df_all = df_long.copy()
    df_all = df_all[df_all["time"].isin([12, 22])].copy()

    df_cells = df_all[df_all["cell"].isin(["HCC1143", "HCC38"])].copy()

    # Force plotting order
    time_order = [12, 22]
    group_order = ["Control", "Migration", "media"]
    x_order = [
        (12, "Control"),
        (12, "Migration"),
        (12, "media"),
        (22, "Control"),
        (22, "Migration"),
        (22, "media"),
    ]

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    print(f"Intotal compounds to plot: {df_cells['compound'].nunique()}")

    for (compound, cell), df_sub in df_cells.groupby(["compound", "cell"]):
        print(f"Start plotting compound: {compound}, cell: {cell}, data shape: {df_sub.shape}, save to: {output_path / f'box_{compound}_{cell}.png'} ")
        fig, ax = plt.subplots(figsize=(8, 5))

        box_data = []
        x_labels = []

        for time_value, group_value in x_order:
            if group_value == "media":
                values = df_all.loc[
                    (df_all["compound"] == compound) &
                    (df_all["cell"] == "media") &
                    (df_all["group"] == "media") &
                    (df_all["time"] == time_value),
                    "value"
                ].dropna()
            else:
                values = df_sub.loc[
                    (df_sub["time"] == time_value) &
                    (df_sub["group"] == group_value),
                    "value"
                ].dropna()

            box_data.append(values)
            x_labels.append(f"{time_value}-{group_value}")

        ax.boxplot(box_data, labels=x_labels, patch_artist=True)
        for i, values in enumerate(box_data, start=1):
            if len(values) == 0:
                continue

            x_jitter = pd.Series(range(len(values)), dtype=float)
            x_jitter = (x_jitter - x_jitter.mean()) * 0.03
            x_positions = i + x_jitter

            ax.scatter(
                x_positions,
                values,
                color="black",
                alpha=0.7,
                s=18,
                zorder=3,
            )

        ax.set_title(f"{compound} | {cell}")
        ax.set_xlabel("Time-Group")
        ax.set_ylabel("Value")
        ax.tick_params(axis="x", rotation=45)
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)

        safe_compound = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(compound))
        safe_cell = "".join(ch if ch.isalnum() or ch in "_-" else "_" for ch in str(cell))
        fig.savefig(output_path / f"box_{safe_compound}_{safe_cell}.png", dpi=300, bbox_inches="tight")
        plt.close(fig)

    return df

if __name__ == "__main__":
    # Read the Migration project df_final.csv file, should come up with a more project relevant naming
    df = pd.read_csv(os.path.join(os.path.dirname(__file__), 'input', "df_final.csv"))
    print("df shape:", df.shape)
    # Shape the final df to df_long format
    df_wide = df.drop(df.columns[[0, 1, 5, 6]], axis=1)
    df_long = df_wide.melt(
        id_vars=["cell", "group", "time"],
        var_name="compound",
        value_name="value"
    )
    print("df_long shape:", df_long.shape)
    # print(df_long)
    # Plot line plots for each compound and save them to the output directory
    plot_df = Migration_line_plots(df_long)
    # Plot box plots for each compound and cell line and save them to the output directory
    box_df = Migration_box_plots(df_long)