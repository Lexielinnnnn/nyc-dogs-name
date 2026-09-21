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
