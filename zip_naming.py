"""Q4: The most common name in each NYC borough, by license record count."""
import pandas as pd
import matplotlib.pyplot as plt

from breed_naming import ROOT, INPUT, get_top_names


def main():
    df = pd.read_csv(INPUT, usecols=["animal_name", "borough"])
    groups = ["Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"]
    result = get_top_names(df, "borough", groups, 1)
    result = result.set_index("borough").loc[groups].reset_index()
    (ROOT / "results").mkdir(exist_ok=True)
    (ROOT / "figures").mkdir(exist_ok=True)
    result.to_csv(ROOT / "results/q4_borough_naming.csv", index=False)

    fig, ax = plt.subplots(figsize=(10, 5))
    labels = result["borough"] + " - " + result["animal_name"]
    bars = ax.barh(labels, result["record_count"], color="steelblue")
    ax.bar_label(bars, labels=[f"{n:,}" for n in result["record_count"]], padding=3)
    ax.invert_yaxis()
    ax.set_xlim(0, result["record_count"].max() * 1.18)
    ax.set_xlabel("License record count")
    ax.set_title("Most common dog name in each borough")
    fig.tight_layout()
    fig.savefig(ROOT / "figures/q4_borough_naming.png", dpi=150)
    plt.close(fig)
    print(result.to_string(index=False))
    print("Saved results/q4_borough_naming.csv and figures/q4_borough_naming.png")


if __name__ == "__main__":
    main()
