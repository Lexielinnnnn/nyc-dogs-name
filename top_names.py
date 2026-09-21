"""
top_names.py
 
Q1: What are the most common dog names in NYC?
    + Comparison against the national Top 100 (Rover.com annual pet-naming
      report, 2025 edition), to see how NYC's naming patterns compare.
 
Input:
    data/clean/nyc_dog_licenses_clean.csv
 
Output:
    output/q1_top_names.csv              -- NYC ranked name frequency table
    output/q1_national_comparison.csv    -- NYC Top 20 vs national Top 100
    figures/q1_top20_bar.png             -- horizontal bar chart of Top 20
"""
 
from __future__ import annotations
 
from pathlib import Path
 
import matplotlib.pyplot as plt
import pandas as pd
 
PROJECT_ROOT = Path(__file__).resolve().parent
CLEAN_PATH = PROJECT_ROOT / "data" / "clean" / "nyc_dog_licenses_clean.csv"
OUTPUT_CSV = PROJECT_ROOT / "output" / "q1_top_names.csv"
OUTPUT_COMPARISON_CSV = PROJECT_ROOT / "output" / "q1_national_comparison.csv"
OUTPUT_FIG = PROJECT_ROOT / "figures" / "q1_top20_bar.png"
 
TOP_N_TABLE = 50
TOP_N_CHART = 20
 
# Source: Rover.com's 2025 annual pet-naming report (survey-based, not
# breed-registration-based -- a better match for this dataset's mixed-breed
# population than AKC's purebred-registration rankings).
# https://www.newsweek.com/americas-most-popular-dog-names-2025-revealed-11059011
NATIONAL_TOP_100_2025 = [
    "Luna", "Bella", "Charlie", "Daisy", "Max", "Lucy", "Milo", "Cooper", "Coco", "Bailey",
    "Lola", "Teddy", "Lily", "Bear", "Rocky", "Sadie", "Penny", "Zoe", "Buddy", "Stella",
    "Nala", "Rosie", "Blu", "Leo", "Maggie", "Willow", "Ruby", "Remi", "Duke", "Beau",
    "Molly", "Ollie", "Roxy", "Tucker", "Millie", "Winston", "Koda", "Oliver", "Nova", "Winnie",
    "Bentley", "Moose", "Ellie", "Bruno", "Murphy", "Pepper", "Finn", "Loki", "Chloe", "Jack",
    "Toby", "Harley", "Zeus", "Piper", "Louie", "Sophie", "Gus", "Scout", "Gracie", "Honey",
    "Hank", "Jax", "Hazel", "Maverick", "Mia", "Archie", "Riley", "Ace", "Callie", "Apollo",
    "Poppy", "Frankie", "Oakley", "Lulu", "Oreo", "Shadow", "Marley", "Olive", "Ginger", "Lucky",
    "Benny", "Goose", "Henry", "Kona", "Cookie", "Maple", "Bandit", "Benji", "Lady", "Athena",
    "Thor", "Dexter", "Sunny", "Cash", "Gunnar", "Peanut", "Ziggy", "Chewy", "Theo", "Simba",
]
 
 
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
 
 
def compare_to_national(nyc_top: pd.DataFrame, national_top_100: list[str]) -> pd.DataFrame:
    """For each NYC top name, show its NYC rank and its national rank (or
    'not in top 100' if it doesn't appear there) -- and vice versa for
    national names that don't crack NYC's list.
    """
    national_rank = {name: i + 1 for i, name in enumerate(national_top_100)}
 
    comparison = nyc_top.copy()
    comparison["national_rank"] = comparison["name"].map(national_rank)
    comparison["in_national_top_100"] = comparison["national_rank"].notna()
 
    return comparison
 
 
def plot_top_names(top_names: pd.DataFrame, top_n_chart: int, output_path: Path) -> None:
    chart_data = top_names.head(top_n_chart).sort_values("count")
 
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
 
    comparison = compare_to_national(top_names.head(20), NATIONAL_TOP_100_2025)
    comparison.to_csv(OUTPUT_COMPARISON_CSV, index=False)
    n_in_national = comparison["in_national_top_100"].sum()
    print(
        f"\nOf NYC's Top 20 names, {n_in_national} also appear in the "
        f"national Top 100 (Rover.com 2025). NYC-distinctive names in the "
        f"top 20: {comparison.loc[~comparison['in_national_top_100'], 'name'].tolist()}"
    )
    print(f"Saved national comparison to {OUTPUT_COMPARISON_CSV}")
 
    plot_top_names(top_names, TOP_N_CHART, OUTPUT_FIG)
 
 
if __name__ == "__main__":
    main()
 
