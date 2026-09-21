"""Q4: Top 5 names in each NYC borough, by license record count."""
import pandas as pd
import matplotlib.pyplot as plt

from breed_naming import ROOT, INPUT, get_top_names


def main():
    df = pd.read_csv(INPUT, usecols=["animal_name", "borough"])
    groups = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    result = get_top_names(df, "borough", groups, 5)
    result = result.set_index("borough").loc[groups].reset_index()
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "figures").mkdir(exist_ok=True)
    result.to_csv(ROOT / "results/q4_borough_naming.csv", index=False)

    fig, axes = plt.subplots(5, 1, figsize=(10, 16), sharex=True)
    for ax, group in zip(axes, groups):
        names = result[result["borough"] == group]
        bars = ax.barh(names["animal_name"], names["record_count"], color="steelblue")
        ax.bar_label(bars, labels=[f"{n:,}" for n in names["record_count"]], padding=3)
        ax.invert_yaxis()
        ax.set_xlim(0, result["record_count"].max() * 1.18)
        ax.set_xlabel("License record count")
        ax.set_title(group)
    fig.suptitle("Top 5 dog names in each borough", fontsize=16)
    fig.tight_layout(rect=(0, 0, 1, 0.97))
    fig.savefig(ROOT / "figures/q4_borough_naming.png", dpi=150)
    plt.close(fig)
    print(result.to_string(index=False))
    print("Saved results/q4_borough_naming.csv and figures/q4_borough_naming.png")


if __name__ == "__main__":
    main()
