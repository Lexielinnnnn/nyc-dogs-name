# Borough mapping

Prepared 2026-09-20 from NYC Department of Health and Mental Hygiene (DOHMH) CSVs:

- ZIP/ZCTA to MODZCTA: https://raw.githubusercontent.com/nychealth/coronavirus-data/master/Geography-resources/ZCTA-to-MODZCTA.csv
- MODZCTA borough labels: https://raw.githubusercontent.com/nychealth/coronavirus-data/master/totals/data-by-modzcta.csv
- Definitions: https://github.com/nychealth/coronavirus-data/tree/master/Geography-resources
- Cross-borough ZIP discussion: https://www.nyc.gov/assets/planning/download/pdf/planning-level/nyc-population/nny2000/newest_new_yorkers_2000.pdf

This is a derived statistical-geography crosswalk, not a complete, current USPS
postal directory. ZIP codes, ZCTAs, and MODZCTAs are distinct geographies. The
source repository is archived. The mapping is approximate and is not proof of
the exact administrative borough of an individual address.

There are 214 unique codes: 212 have borough labels. ZIP 10463 crosses
Bronx/Manhattan, and 11370 crosses Queens/Bronx. Their boroughs are left blank
instead of adopting the source's single statistical borough label. The source
placeholder 99999 was excluded. Unmatched codes must not be assigned by prefix
or automatically classified as outside NYC.

The cleaning script uses a many-to-one left join and retains unassigned records.
For borough comparisons, filter to nonmissing borough AND valid animal_name;
report excluded counts. Overall name analysis can retain records without borough
labels. Use each borough's valid-name record count as its percentage denominator.

Original ZipCode, Borough, MODZCTA, and MappingStatus fields are retained in the
reference CSV. The cleaned dataset uses snake_case column names.
