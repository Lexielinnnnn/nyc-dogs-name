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
    4. Normalizes breed whitespace/casing, preserving mixed-breed labels.
    5. Validates ZIP format and adds approximate borough groups from a crosswalk.
    6. Flags likely duplicate license renewals for the same dog, since this
       dataset has no persistent per-dog ID -- each row is a license
       *period*, so the same dog can appear many times across years.
       We approximate "same dog" via (name, gender, breed, zip, birth year)
       and flag all matching records without deleting them. This is
       a known limitation, not a guarantee of one row per real dog.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "nyc_dog_licenses_raw.csv"
CLEAN_PATH = PROJECT_ROOT / "data" / "clean" / "nyc_dog_licenses_clean.csv"
MAPPING_PATH = PROJECT_ROOT / "data" / "reference" / "nyc_zip_to_borough.csv"

# Candidate raw column names -> the standardized name we'll use downstream.
# Add to these lists if your export uses a header not listed here.
COLUMN_ALIASES: dict[str, list[str]] = {
    "animal_name": ["animalname", "animal_name"],
    "gender": ["animalgender", "gender", "sex"],
    "birth_year_raw": ["animalbirthyear", "animal_birth_year", "animalbirth"],
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
    "NAME",
    "NAME NOT PROVIDED",
    "NAME NOT PROVI",
    "UNKNOWN",
    "N/A",
    "NA",
    "NONE",
    ".",
    "UNNAMED",
    "NAN",
    "NULL",
    "<NA>",
}

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
        raise ValueError(f"Expected columns not found: {missing}. Raw columns: {list(df.columns)}")
    return df


def clean_names(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True).str.upper()
    invalid = cleaned.isin(PLACEHOLDER_NAMES) | cleaned.str.fullmatch(r"\d+", na=False)
    cleaned = cleaned.mask(invalid)
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
    cleaned = series.astype("string").str.strip().str.replace(r"\s+", " ", regex=True)
    cleaned = cleaned.str.strip().str.title()
    cleaned = cleaned.mask(cleaned.str.upper().isin(PLACEHOLDER_NAMES))
    return cleaned


def clean_zip(series: pd.Series) -> pd.Series:
    cleaned = series.astype("string").str.strip().str.replace(r"\.0+$", "", regex=True)
    cleaned = cleaned.str.replace(r"^(\d{5})-\d{4}$", r"\1", regex=True)
    cleaned = cleaned.where(cleaned.str.fullmatch(r"\d{5}", na=False))
    return cleaned.mask(cleaned.isin(["00000", "99999"]))


def add_borough(df: pd.DataFrame, mapping_path: Path) -> pd.DataFrame:
    """Keep every record; leave ambiguous and unmatched boroughs unassigned."""
    mapping = pd.read_csv(mapping_path, dtype="string", keep_default_na=False)
    required = {"ZipCode", "Borough", "MODZCTA", "MappingStatus"}
    if not required.issubset(mapping.columns):
        raise ValueError(f"Mapping requires columns: {sorted(required)}")
    mapping = mapping.rename(columns={
        "ZipCode": "zip_code", "Borough": "borough", "MODZCTA": "modzcta",
        "MappingStatus": "borough_mapping_status",
    })
    mapping["zip_code"] = clean_zip(mapping["zip_code"])
    if mapping["zip_code"].isna().any() or mapping["zip_code"].duplicated().any():
        raise ValueError("Mapping ZIP codes must be valid and unique.")
    mapping["borough"] = mapping["borough"].str.strip().replace("", pd.NA)
    boroughs = {"Manhattan", "Brooklyn", "Queens", "Bronx", "Staten Island"}
    if not set(mapping["borough"].dropna()).issubset(boroughs):
        raise ValueError("Unexpected borough label in the mapping.")
    ambiguous = mapping["zip_code"].isin(["10463", "11370"])
    mapping.loc[ambiguous, "borough"] = pd.NA
    mapping.loc[ambiguous, "borough_mapping_status"] = "Ambiguous: crosses borough boundaries"
    # Preserve an existing source borough rather than creating merge suffixes.
    if "borough" in df.columns:
        df = df.rename(columns={"borough": "borough_original"})
    result = df.merge(
        mapping[["zip_code", "borough", "modzcta", "borough_mapping_status"]],
        on="zip_code", how="left", validate="many_to_one",
    )
    assert len(result) == len(df), "Borough join changed the record count."
    result["borough_mapping_status"] = result["borough_mapping_status"].replace("", pd.NA).fillna("Unmatched ZIP")
    result.loc[result["zip_code"].isna(), "borough_mapping_status"] = "Missing or invalid ZIP"
    return result


def flag_duplicate_licenses(df: pd.DataFrame) -> pd.DataFrame:
    """Flag possible repeated licenses without removing any records.

    Limitation: with no persistent per-dog ID in this dataset, this is an
    approximation, not a guarantee. Two different dogs with the same name,
    breed, gender, ZIP, and birth year would be incorrectly merged (rare
    but possible); a renewed dog whose owner moved ZIP codes would be
    incorrectly treated as two dogs. Missing identity fields are not matched.
    The flag is not proof that records describe the same dog.
    """
    key_cols = ["animal_name", "gender", "breed_name", "zip_code", "birth_year"]
    df["possible_repeat_license"] = False
    if all(c in df.columns for c in key_cols):
        complete = df[key_cols].notna().all(axis=1)
        df.loc[complete, "possible_repeat_license"] = df.loc[complete].duplicated(key_cols, keep=False)
    print(f"Possible repeated-license records retained: {df['possible_repeat_license'].sum():,}")
    return df


def clean(raw_path: Path, clean_path: Path) -> None:
    df = pd.read_csv(raw_path, dtype="string")
    raw_rows = len(df)
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
        df["zip_code_original"] = df["zip_code"]
        df["zip_code"] = clean_zip(df["zip_code"])

    for date_col in ["license_issued_date", "license_expired_date"]:
        if date_col in df.columns:
            df[date_col] = pd.to_datetime(df[date_col], errors="coerce")

    # Drop rows with no usable name -- they can't contribute to a
    # naming-pattern analysis.
    before = len(df)
    df = df.dropna(subset=["animal_name"])
    removed_names = before - len(df)
    print(f"Dropped {before - len(df)} rows with missing/placeholder names.")

    df = add_borough(df, MAPPING_PATH)
    df = flag_duplicate_licenses(df)

    clean_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(clean_path, index=False)
    report = {
        "raw_rows": raw_rows,
        "invalid_names_removed": removed_names,
        "clean_rows": len(df),
        "unit": "license record",
        "mapped_borough_rows": int(df["borough"].notna().sum()),
        "borough_match_rate": float(df["borough"].notna().mean()) if len(df) else None,
        "mapping_status_counts": df["borough_mapping_status"].value_counts().to_dict(),
        "possible_repeat_license_rows": int(df["possible_repeat_license"].sum()),
    }
    clean_path.with_suffix(".report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    df.loc[df["borough"].isna()].groupby(
        ["zip_code_original", "zip_code", "borough_mapping_status"], dropna=False
    ).size().reset_index(name="record_count").to_csv(clean_path.with_suffix(".unmatched_zips.csv"), index=False)
    print(f"Borough groups assigned: {report['mapped_borough_rows']:,} / {len(df):,}")
    print(f"Saved {len(df)} cleaned rows to {clean_path}")


if __name__ == "__main__":
    if not RAW_PATH.exists():
        print(f"Raw file not found at {RAW_PATH}. Run fetch_data.py first.", file=sys.stderr)
        sys.exit(1)
    clean(RAW_PATH, CLEAN_PATH)
