"""Q3: Top 5 names in the ten most common breeds, by license record count."""
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
INPUT = ROOT / "data/clean/nyc_dog_licenses_clean.csv"


def get_top_names(df, group_column, groups, top_n):
    counts = df.groupby([group_column, "animal_name"]).size().reset_index(name="record_count")
    counts = counts[counts[group_column].isin(groups)]
    # Break equal counts alphabetically for a consistent display.
    counts = counts.sort_values(
        [group_column, "record_count", "animal_name"], ascending=[True, False, True]
    )
    return counts.groupby(group_column).head(top_n).reset_index(drop=True)


def main():
    df = pd.read_csv(INPUT, usecols=["animal_name", "breed_name"])
    groups = df["breed_name"].value_counts().head(10).index.tolist()
    result = get_top_names(df, "breed_name", groups, 5)
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "figures").mkdir(exist_ok=True)
    result.to_csv(ROOT / "results/q3_breed_naming.csv", index=False)

    fig, axes = plt.subplots(5, 2, figsize=(14, 17), sharex=True)
    for ax, group in zip(axes.flat, groups):
        names = result[result["breed_name"] == group].iloc[::-1]
        bars = ax.barh(names["animal_name"], names["record_count"], color="steelblue")
        ax.bar_label(bars, labels=[f"{n:,}" for n in names["record_count"]], padding=3)
        ax.set_title(group)
        ax.set_xlabel("License record count")
        ax.set_xlim(0, result["record_count"].max() * 1.18)
    fig.suptitle("Top 5 names in the 10 most common breeds", fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(ROOT / "figures/q3_breed_naming.png", dpi=150)
    plt.close(fig)
    print(result.to_string(index=False))
    print("Saved results/q3_breed_naming.csv and figures/q3_breed_naming.png")


if __name__ == "__main__":
    main()
