"""
fetch_data.py

Downloads the NYC Dog Licensing Dataset (Socrata dataset ID: nu7n-tubp)
as a raw CSV file for the project.

Usage:
    python fetch_data.py

Optional:
    Set the NYC_OPEN_DATA_APP_TOKEN environment variable with a Socrata
    app token to avoid throttling on large downloads. Get a free token at:
    https://data.cityofnewyork.us/profile/edit/developer_settings
"""

import os
import sys
from pathlib import Path

import requests

# The v3 "query.csv" endpoint exports the full dataset as CSV.
# You can optionally append SoQL parameters to the query string, e.g.
# "&$select=animalname,animalbirth,breedname,zipcode,borough,gender"
# to only pull the columns you actually need (smaller file, faster).
DATASET_ID = "nu7n-tubp"
BASE_URL = f"https://data.cityofnewyork.us/api/v3/views/{DATASET_ID}/query.csv"

# If you'd rather pull only the columns needed for the dog-names story,
# uncomment SELECT_COLUMNS and pass it into fetch_csv() below.
SELECT_COLUMNS = [
    "animalname",
    "animalgender",
    "animalbirthyr",
    "breedname",
    "zipcode",
    "borough",
    "licenseissueddate",
    "licenseexpireddate",
]

OUTPUT_PATH = Path("data/raw/nyc_dog_licenses_raw.csv")


def fetch_csv(output_path: Path, select_columns: list[str] | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    params = {}
    if select_columns:
        params["$select"] = ",".join(select_columns)

    app_token = os.environ.get("NYC_OPEN_DATA_APP_TOKEN")
    headers = {"X-App-Token": app_token} if app_token else {}

    print(f"Requesting: {BASE_URL}")
    if params:
        print(f"With params: {params}")

    with requests.get(
        BASE_URL, params=params, headers=headers, stream=True, timeout=120
    ) as response:
        response.raise_for_status()
        total_bytes = 0
        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)
                total_bytes += len(chunk)

    print(f"Saved {total_bytes / 1_000_000:.1f} MB to {output_path}")


if __name__ == "__main__":
    try:
        # Swap in SELECT_COLUMNS here if you want a slimmer raw file:
        # fetch_csv(OUTPUT_PATH, select_columns=SELECT_COLUMNS)
        fetch_csv(OUTPUT_PATH)
    except requests.HTTPError as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)


"""
clean_data.py

Cleans the raw NYC Dog Licensing Dataset CSV (fetched by fetch_data.py)
into an analysis-ready file for the dog-naming story.

Usage:
    python clean_data.py

Input:
    data/raw/nyc_dog_licenses_raw.csv

Output:
    data/clean/nyc_dog_licenses_clean.csv

What this does (see project README / doc for the reasoning behind each step):
    1. Normalizes column names (the raw export's headers vary slightly by
       download date, so we match on a set of known aliases per field).
    2. Cleans dog names: trims whitespace, standardizes case, and drops
       placeholder / non-name values (e.g. "NAME NOT PROVIDED", "UNKNOWN").
    3. Extracts a usable birth year, whether the raw column is a full year
       or a year-month value.
    4. Normalizes breed names (trims whitespace/casing, strips common
       suffixes like "(Mix)" so the same breed doesn't fragment into
       multiple labels).
    5. Validates ZIP codes (must be a plausible 5-digit NYC-area code).
    6. Flags likely duplicate license renewals for the same dog, since this
       dataset has no persistent per-dog ID -- each row is a license
       *period*, so the same dog can appear many times across years.
       We approximate "same dog" via (name, gender, breed, zip, birth year)
       and keep only the first (earliest-issued) record per group. This is
       a known limitation -- documented in the ethics/limitations section,
       not a guarantee of one row per real dog.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "nyc_dog_licenses_raw.csv"
CLEAN_PATH = PROJECT_ROOT / "data" / "clean" / "nyc_dog_licenses_clean.csv"

# Candidate raw column names -> the standardized name we'll use downstream.
# Add to these lists if your export uses a header not listed here.
COLUMN_ALIASES: dict[str, list[str]] = {
    "animal_name": ["animalname", "animal_name"],
    "gender": ["animalgender", "gender", "sex"],
    "birth_year_raw": ["animalbirthyear", "animal_birth_year"],
    "birth_month_raw": ["animalbirthmonth", "animal_birth_month"],
    "breed_name": ["breedname", "breed_name", "breed"],
    "zip_code": ["zipcode", "zip_code", "zip"],
    "borough": ["borough"],
    "license_issued_date": ["licenseissueddate", "license_issued_date"],
    "license_expired_date": ["licenseexpireddate", "license_expired_date"],
    "extract_year": ["extractyear", "extract_year"],
}

# Values that mean "no real name was given," seen in this dataset.
PLACEHOLDER_NAMES = {
    "",
    "NAME NOT PROVIDED",
    "NAME NOT PROVI",
    "UNKNOWN",
    "N/A",
    "NA",
    "NONE",
    ".",
    "UNNAMED",
}

# Suffixes/qualifiers to strip from breed names so variants collapse
# into one consistent label (e.g. "Labrador Retriever (Cross)" ->
# "Labrador Retriever").
BREED_SUFFIX_PATTERN = re.compile(
    r"\s*\((?:cross|mix|or mix)\)\s*$|,?\s*crossbreed\s*$",
    flags=re.IGNORECASE,
)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Rename raw columns to standardized names using COLUMN_ALIASES."""
    lower_map = {c.lower().replace(" ", "").replace("_", ""): c for c in df.columns}
    rename_map = {}
    for standard_name, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            key = alias.lower().replace(" ", "").replace("_", "")
            if key in lower_map:
                rename_map[lower_map[key]] = standard_name
                break
    df = df.rename(columns=rename_map)
    missing = [c for c in ["animal_name", "breed_name", "zip_code"] if c not in df.columns]
    if missing:
        print(
            f"WARNING: expected columns not found: {missing}. "
            f"Raw columns are: {list(df.columns)}",
            file=sys.stderr,
        )
    return df


def clean_names(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.strip().str.upper()
    cleaned = cleaned.where(~cleaned.isin(PLACEHOLDER_NAMES), other=pd.NA)
    # Title-case for readability in charts/tables (e.g. "BELLA" -> "Bella").
    return cleaned.str.title()


def extract_birth_year(df: pd.DataFrame) -> pd.Series:
    if "birth_year_raw" in df.columns:
        year = pd.to_numeric(df["birth_year_raw"], errors="coerce")
    elif "birth_month_raw" in df.columns:
        # Handles formats like "201401", "2014-01", or "01/2014".
        raw = df["birth_month_raw"].astype(str)
        year = raw.str.extract(r"(20\d{2}|19\d{2})", expand=False)
        year = pd.to_numeric(year, errors="coerce")
    else:
        return pd.Series([pd.NA] * len(df), index=df.index)

    current_year = pd.Timestamp.now().year
    year = year.where(year.between(1990, current_year), other=pd.NA)
    return year


def clean_breed(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.strip()
    cleaned = cleaned.str.replace(BREED_SUFFIX_PATTERN, "", regex=True)
    cleaned = cleaned.str.strip().str.title()
    cleaned = cleaned.replace({"Unknown": pd.NA, "": pd.NA, "Nan": pd.NA})
    return cleaned


def clean_zip(series: pd.Series) -> pd.Series:
    cleaned = series.astype(str).str.extract(r"(\d{5})", expand=False)
    # Basic sanity check: NYC-area ZIP codes fall in this range.
    numeric = pd.to_numeric(cleaned, errors="coerce")
    cleaned = cleaned.where(numeric.between(10000, 11697), other=pd.NA)
    return cleaned


def flag_duplicate_licenses(df: pd.DataFrame) -> pd.DataFrame:
    """Keep only the earliest license record per approximate dog identity.

    Limitation: with no persistent per-dog ID in this dataset, this is an
    approximation, not a guarantee. Two different dogs with the same name,
    breed, gender, ZIP, and birth year would be incorrectly merged (rare
    but possible); a renewed dog whose owner moved ZIP codes would be
    incorrectly treated as two dogs. Document this in the write-up.
    """
    key_cols = [c for c in ["animal_name", "gender", "breed_name", "zip_code", "birth_year"] if c in df.columns]
    if not key_cols:
        return df

    sort_col = "license_issued_date" if "license_issued_date" in df.columns else None
    if sort_col:
        df = df.sort_values(sort_col)

    before = len(df)
    df = df.drop_duplicates(subset=key_cols, keep="first")
    after = len(df)
    print(f"Deduplication: {before - after} likely renewal rows dropped ({before} -> {after}).")
    return df


def clean(raw_path: Path, clean_path: Path) -> None:
    df = pd.read_csv(raw_path, low_memory=False)
    print(f"Loaded {len(df)} raw rows with columns: {list(df.columns)}")

    df = normalize_columns(df)

    if "animal_name" in df.columns:
        df["animal_name"] = clean_names(df["animal_name"])

    df["birth_year"] = extract_birth_year(df)
    # Drop the intermediate raw column(s) now that birth_year is derived,
    # so the cleaned file has one unambiguous birth-year column instead of
    # both the original and the derived version.
    df = df.drop(columns=[c for c in ["birth_year_raw", "birth_month_raw"] if c in df.columns])

    if "breed_name" in df.columns:
        df["breed_name"] = clean_breed(df["breed_name"])

    if "zip_code" in df.columns:
        df["zip_code"] = clean_zip(df["zip_code"])

    for date_col in ["license_issued_date", "license_expired_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Drop rows with no usable name -- they can't contribute to a
    # naming-pattern analysis.
    before = len(df)
    df = df.dropna(subset=["animal_name"])
    print(f"Dropped {before - len(df)} rows with missing/placeholder names.")

    df = flag_duplicate_licenses(df)

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(clean_path, index=False)
    print(f"Saved {len(df)} cleaned rows to {clean_path}")


if __name__ == "__main__":
    if not RAW_PATH.exists():
        print(f"Raw file not found at {RAW_PATH}. Run fetch_data.py first.", file=sys.stderr)
        sys.exit(1)
    clean(RAW_PATH, CLEAN_PATH)
