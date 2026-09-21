"""
q1_top_names.py
 
Q1: What are the most common dog names in NYC?
 
Input:
    data/clean/nyc_dog_licenses_clean.csv   (produced by build_dataset.py / clean_data.py)
 
Output:
    analysis/output/q1_top_names.csv        -- ranked name frequency table
    figures/q1_top20_bar.png                -- horizontal bar chart of Top 20
 
Note: this question does NOT use birth_decade or name_rank_by_year -- those
are for Q2 (name trends over time). Q1 is a simple citywide frequency count.
"""
 
from __future__ import annotations
 
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd
 
PROJECT_ROOT = Path(__file__).resolve().parent
CLEAN_PATH = PROJECT_ROOT / "data" / "clean" / "nyc_dog_licenses_clean.csv"
OUTPUT_CSV = PROJECT_ROOT / "analysis" / "output" / "q1_top_names.csv"
OUTPUT_FIG = PROJECT_ROOT / "figures" / "q1_top20_bar.png"
 
TOP_N_TABLE = 50   # how many rows to save in the CSV
TOP_N_CHART = 20   # how many to show in the bar chart
 
 
def compute_top_names(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    counts = (
        df["animal_name"]
        .value_counts()
        .head(top_n)
        .rename_axis("name")
        .reset_index(name="count")
    )
    counts.insert(0, "rank", range(1, len(counts) + 1))
    return counts
 
 
def plot_top_names(top_names: pd.DataFrame, top_n_chart: int, output_path: Path) -> None:
    chart_data = top_names.head(top_n_chart).sort_values("count")  # ascending for horizontal bar
 
    fig, ax = plt.subplots(figsize=(8, 8))
    ax.barh(chart_data["name"], chart_data["count"], color="#c1440e")
    ax.set_xlabel("Number of licensed dogs")
    ax.set_title(f"Top {top_n_chart} Most Common Dog Names in NYC")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
 
    for i, (name, count) in enumerate(zip(chart_data["name"], chart_data["count"])):
        ax.text(count, i, f" {count:,}", va="center", fontsize=9)
 
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    print(f"Saved chart to {output_path}")
 
 
def main() -> None:
    df = pd.read_csv(CLEAN_PATH, low_memory=False)
    print(f"Loaded {len(df)} cleaned rows.")
 
    top_names = compute_top_names(df, TOP_N_TABLE)
 
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    top_names.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved ranked name table to {OUTPUT_CSV}")
    print(top_names.head(10).to_string(index=False))
 
    plot_top_names(top_names, TOP_N_CHART, OUTPUT_FIG)
 
 
if __name__ == "__main__":
    main()
 
