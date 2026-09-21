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
import csv
from pathlib import Path

import requests

# Download all pages with stable ordering and verify the record count.
DATASET_ID = "nu7n-tubp"
BASE_URL = f"https://data.cityofnewyork.us/resource/{DATASET_ID}.json"

# Default API fields; borough is derived from ZIP codes during cleaning.
SELECT_COLUMNS = [
    "animalname",
    "animalgender",
    "animalbirth",
    "breedname",
    "zipcode",
    "licenseissueddate",
    "licenseexpireddate",
    "extract_year",
]

PROJECT_ROOT = Path(__file__).resolve().parent
OUTPUT_PATH = PROJECT_ROOT / "data/raw/nyc_dog_licenses_raw.csv"


def fetch_csv(output_path: Path, select_columns: list[str] | None = None) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    columns = select_columns if select_columns is not None else SELECT_COLUMNS

    app_token = os.environ.get("NYC_OPEN_DATA_APP_TOKEN")
    headers = {"X-App-Token": app_token} if app_token else {}

    print(f"Requesting: {BASE_URL}")

    def query(params):
        with requests.get(BASE_URL, params=params, headers=headers, timeout=120) as response:
            response.raise_for_status()
            result = response.json()
        if not isinstance(result, list):
            raise ValueError("Expected a list of API records.")
        return result

    def get_count():
        return int(query({"$select": "count(*) AS total"})[0]["total"])

    expected = get_count()
    if expected == 0:
        raise ValueError("API returned no records; the existing CSV was not replaced.")

    page_size, offset, downloaded = 50_000, 0, 0
    seen_ids = set()
    temporary_path = output_path.with_suffix(".csv.part")
    try:
        with temporary_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["api_row_id", *columns])
            writer.writeheader()
            while True:
                rows = query({
                    "$select": ":id AS api_row_id," + ",".join(columns),
                    "$limit": page_size,
                    "$offset": offset,
                    "$order": ":id",
                })
                for row in rows:
                    row_id = row.get("api_row_id")
                    if row_id is None or row_id in seen_ids:
                        raise ValueError("Missing or duplicate API row ID; retry download.")
                    seen_ids.add(row_id)
                writer.writerows(rows)
                downloaded += len(rows)
                print(f"Downloaded {downloaded:,} / {expected:,} records")
                if len(rows) < page_size:
                    break
                offset += page_size

        if downloaded != expected or get_count() != expected:
            raise ValueError("Record count changed or download is incomplete; retry download.")
        # These checks cannot detect every concurrent edit; keep this snapshot.
        temporary_path.replace(output_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()

    print(f"Saved {downloaded:,} records to {output_path}")


if __name__ == "__main__":
    try:
        fetch_csv(OUTPUT_PATH)
    except (requests.RequestException, OSError, ValueError) as e:
        print(f"Request failed: {e}", file=sys.stderr)
        sys.exit(1)
