"""
name_trends.py
 
Q2: Do dog names differ by age (birth year)?
 
Input:
    data/clean/nyc_dog_licenses_clean.csv   (must have a 'birth_year' column)
 
Output:
    output/q2_top_names_by_decade.csv   -- top names per birth-year bucket
    output/q2_chi_square_result.txt     -- chi-square test result + interpretation
    figures/q2_trend_lines.png          -- popularity curves for selected names
 
Note: this question DOES use a birth-year bucket (birth_decade / 5yr bucket)
and a per-year name ranking -- unlike Q1, which is a plain citywide count.
"""
 
from __future__ import annotations
 
from pathlib import Path
 
import matplotlib.pyplot as plt
import pandas as pd
from scipy.stats import chi2_contingency
 
PROJECT_ROOT = Path(__file__).resolve().parent
CLEAN_PATH = PROJECT_ROOT / "data" / "clean" / "nyc_dog_licenses_clean.csv"
OUTPUT_CSV = PROJECT_ROOT / "output" / "q2_top_names_by_decade.csv"
OUTPUT_CHI2 = PROJECT_ROOT / "output" / "q2_chi_square_result.txt"
OUTPUT_FIG = PROJECT_ROOT / "figures" / "q2_trend_lines.png"
 
BUCKET_SIZE_YEARS = 5     # use 5-year buckets instead of full decades for more stable samples
TOP_N_PER_BUCKET = 10     # how many top names to list per bucket
N_NAMES_FOR_TREND_CHART = 5   # how many individual names to plot as trend lines
MIN_TOTAL_COUNT_FOR_CHI2 = 20  # only include names with at least this many total records in the test
 
 
def add_birth_bucket(df: pd.DataFrame, bucket_size: int) -> pd.DataFrame:
    df = df.dropna(subset=["birth_year"]).copy()
    df["birth_year"] = df["birth_year"].astype(int)
    bucket_start = (df["birth_year"] // bucket_size) * bucket_size
    df["birth_bucket"] = bucket_start.astype(str) + "-" + (bucket_start + bucket_size - 1).astype(str)
    return df
 
 
def top_names_per_bucket(df: pd.DataFrame, top_n: int) -> pd.DataFrame:
    grouped = (
        df.groupby("birth_bucket")["animal_name"]
        .value_counts()
        .groupby(level=0, group_keys=False)
        .head(top_n)
        .rename("count")
        .reset_index()
    )
    grouped["rank"] = grouped.groupby("birth_bucket")["count"].rank(method="first", ascending=False).astype(int)
    grouped = grouped.sort_values(["birth_bucket", "rank"])
    return grouped[["birth_bucket", "rank", "animal_name", "count"]]
 
 
def plot_name_trends(df: pd.DataFrame, n_names: int, output_path: Path) -> None:
    top_overall = df["animal_name"].value_counts().head(n_names).index.tolist()
 
    trend = (
        df[df["animal_name"].isin(top_overall)]
        .groupby(["birth_year", "animal_name"])
        .size()
        .reset_index(name="count")
    )
 
    fig, ax = plt.subplots(figsize=(9, 6))
    for name in top_overall:
        subset = trend[trend["animal_name"] == name].sort_values("birth_year")
        ax.plot(subset["birth_year"], subset["count"], marker="o", label=name)
 
    ax.set_xlabel("Birth year")
    ax.set_ylabel("Number of licensed dogs")
    ax.set_title(f"Popularity Trends for Top {n_names} Dog Names by Birth Year")
    ax.legend(title="Name")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
 
    fig.tight_layout()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150)
    print(f"Saved trend chart to {output_path}")
 
 
def run_chi_square(df: pd.DataFrame, min_total: int) -> str:
    """Test whether the distribution of (a subset of) names differs across
    birth-year buckets. Only names with enough total records are included,
    since chi-square assumes reasonably sized expected counts per cell.
    """
    name_totals = df["animal_name"].value_counts()
    eligible_names = name_totals[name_totals >= min_total].index
 
    contingency = (
        df[df["animal_name"].isin(eligible_names)]
        .groupby(["birth_bucket", "animal_name"])
        .size()
        .unstack(fill_value=0)
    )
 
    chi2, p_value, dof, _ = chi2_contingency(contingency)
 
    interpretation = (
        "statistically significant (p < 0.05) -- name popularity does appear "
        "to shift across birth-year buckets"
        if p_value < 0.05
        else "not statistically significant (p >= 0.05) at this threshold"
    )
 
    result = (
        f"Chi-square test: name distribution across birth-year buckets\n"
        f"Names included (>= {min_total} total records): {len(eligible_names)}\n"
        f"Birth-year buckets: {list(contingency.index)}\n"
        f"chi2 = {chi2:.2f}, degrees of freedom = {dof}, p-value = {p_value:.4g}\n"
        f"Interpretation: {interpretation}\n"
    )
    return result
 
 
def main() -> None:
    df = pd.read_csv(CLEAN_PATH, low_memory=False)
    print(f"Loaded {len(df)} cleaned rows.")
 
    df = add_birth_bucket(df, BUCKET_SIZE_YEARS)
    print(f"Birth-year buckets found: {sorted(df['birth_bucket'].unique())}")
 
    top_by_bucket = top_names_per_bucket(df, TOP_N_PER_BUCKET)
    OUTPUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    top_by_bucket.to_csv(OUTPUT_CSV, index=False)
    print(f"Saved top names per bucket to {OUTPUT_CSV}")
 
    plot_name_trends(df, N_NAMES_FOR_TREND_CHART, OUTPUT_FIG)
 
    chi2_result = run_chi_square(df, MIN_TOTAL_COUNT_FOR_CHI2)
    OUTPUT_CHI2.write_text(chi2_result, encoding="utf-8")
    print(chi2_result)
 
 
if __name__ == "__main__":
    main()