# Practical next-step suggestions — 5 November 2026

Scan results and Analytics → AI Farm Insights now include practical care actions,
rather than stopping at a grade or a generic request to inspect the fruit.

- Routine care: check soil moisture and drainage; avoid drought during fruit
  development and waterlogging; confirm maturity and handle harvested fruit gently.
- Possible sunburn: inspect sun-facing fruit/stems and consider locally suitable
  protective shade if heat damage is confirmed.
- Possible pest damage: inspect for insects, punctures and bird marks; record the
  observed cause, improve sanitation and obtain pest-specific advice.
- Possible rot/canker/fungal symptoms: inspect and separate confirmed damaged
  harvested fruit, reduce splash/prolonged wetness, maintain appropriate airflow
  and clean tools.
- Lower quality flags: identify and record the actual defect before attributing
  it to water or fertilizer problems.
- The last care action asks users to recheck the same fruit under similar lighting,
  record their changes and seek help if damage spreads or tissue softens.

Analytics chooses care actions from the most frequent saved symptom flag, with
deterministic tie handling. It still describes the records as image-based flags,
not a diagnosis of a farm. Normal scans also receive useful care actions. Existing
saved scan assessments are preserved; new scan records retain the new advice.

Guidance is local and rule-based, works offline, and does not prescribe chemicals,
dosages or nutrient diagnoses from image grades. Detailed guidance remains English
under the current language setting policy. External sources require connectivity.

Primary references, also linked from the new scan and insight guidance:

- UF/IFAS, growing and harvest practices:
  <https://ask.ifas.ufl.edu/publication/HS303>
- UF/IFAS, stem/fruit canker and sanitation:
  <https://edis.ifas.ufl.edu/publication/PP355/pdf>
- Northern Territory Agriculture, drainage and pest/fruit damage:
  <https://nt.gov.au/industry/agriculture/food-crops-plants-and-quarantine/fruit-crops/dragon-fruit-pitaya>

These sources inform general care checks; regional schedules and chemical
recommendations were not transferred into the app. Users are directed to confirm
local suitability and the actual problem before choosing treatment.

Regression checks cover condition-specific advice, lower-grade follow-up, the last
recheck action, dominant-flag selection and useful actions for unflagged scans.

Verification: all **120 JavaScript tests passed**, and Android synchronization,
debug APK build and lint passed. The APK is
`android/app/build/outputs/apk/debug/app-debug.apk` (168,005,929 bytes), SHA-256
`7d8e065ed6f37d80dff58e5e246b49bfe9df0890110141493a0dda5be058ee0f`.
