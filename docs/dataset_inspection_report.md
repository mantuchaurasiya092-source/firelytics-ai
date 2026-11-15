# Firelytics AI NASA Dataset Inspection Report

**Project:** Firelytics AI  
**Team:** Buddy Coders  
**Challenge:** Flame in Freefall — SI-Powered Fire Safety Insights from Microgravity Combustion Data

## 1. Executive Summary

**Overall status: VERIFIED — the downloaded directory contains metadata exports and one engineering document, but no locally available experimental measurements.** The directory contains 9 files (8 TXT, 1 PDF), 5,431,281 bytes total (5.18 MiB / 5.43 MB decimal). There are no zero-byte files. All four `s_PSI-*.txt` files are identical 56-byte placeholder tables containing `Do not use this`; they are not empty and provide no samples. The only PDF is structurally recognizable as a PDF by its `%PDF-1.4` header and end-of-file marker; its text could not be extracted because no PDF extraction library or command-line extractor is installed.

Four non-empty `i_Investigation.txt` exports identify PSI-107 (SPICE), PSI-62 (concurrent flame-spread modeling), PSI-69 (FLEX), and PSI-98 (SAFFIRE-I). These are study metadata: they describe objectives, conditions, instruments, anticipated or reported variables, and publications, but do not include the numerical observations themselves. NASA PSI web records corroborate these PSI identifiers and associate the local SAME EIRD filename with the PSI-101 Engineering Documents category. Local evidence does not establish that the PDF contains measured data or reveal its contents.

**Recommendation:** Prioritize SAFFIRE-I as the MVP's target data source because the official NASA record describes a large-scale microgravity fire and complementary measurements of temperature, pressure, O2, CO2, flow, radiation, and imagery. Do not begin analytics on purported NASA observations until raw or analyzed measurements are acquired from the official PSI record and their units, sampling, calibration, and provenance are checked.

## 2. Inspection Date and Environment

- Inspection date: 2026-11-14 (system date supplied for this inspection).
- Environment: Windows 11 / Windows PowerShell 5.1; project root `C:\Users\mantu\firelytics-ai`; source directory `D:\DATASETS 2`.
- Methods: recursive PowerShell file enumeration; byte lengths and last-write timestamps; `Get-FileHash -Algorithm SHA256`; byte-level checks of the sample TXT files; PDF header and trailer-marker checks; complete reads of all four `i_Investigation.txt` exports; online checks of official NASA PSI records.
- PDF inspection limitation: `fitz`/PyMuPDF, `pypdf`, `PyPDF2`, `pdfminer`, and `pdfplumber` were not installed; `pdftotext`, `mutool`, and `qpdf` were not available as commands. No software was installed and no OCR was used.
- Original files were not modified, moved, renamed, or deleted.

## 3. Complete Dataset Inventory

All timestamps below are local file-system last-write times as reported by PowerShell. Size in MiB uses 1 MiB = 1,048,576 bytes. The exact SHA-256 values are repeated in Section 15.

| Relative path | Exact filename | Extension | Bytes | MiB | Last modified | Empty? | Detected format |
|---|---|---:|---:|---:|---|---|---|
| `PSI-107_metadata_PSI-176_SPICE\i_Investigation.txt` | `i_Investigation.txt` | `.txt` | 9,019 | 0.0086 | 2026-11-14 14:06:26 | No | Readable plain-text metadata export |
| `PSI-107_metadata_PSI-176_SPICE\s_PSI-107.txt` | `s_PSI-107.txt` | `.txt` | 56 | 0.0001 | 2026-11-14 14:06:26 | No | Readable tab-delimited placeholder |
| `PSI-62_metadata_NEWID-7_Concurrent Flame Spr\i_Investigation.txt` | `i_Investigation.txt` | `.txt` | 9,402 | 0.0090 | 2026-11-14 13:56:50 | No | Readable plain-text metadata export |
| `PSI-62_metadata_NEWID-7_Concurrent Flame Spr\s_PSI-62.txt` | `s_PSI-62.txt` | `.txt` | 56 | 0.0001 | 2026-11-14 13:56:52 | No | Readable tab-delimited placeholder |
| `PSI-69_metadata_PSI-133_FLEX\i_Investigation.txt` | `i_Investigation.txt` | `.txt` | 24,488 | 0.0234 | 2026-11-14 14:04:36 | No | Readable plain-text metadata export |
| `PSI-69_metadata_PSI-133_FLEX\s_PSI-69.txt` | `s_PSI-69.txt` | `.txt` | 56 | 0.0001 | 2026-11-14 14:04:36 | No | Readable tab-delimited placeholder |
| `PSI-98_metadata_PSI-166_SAFFIRE-I\i_Investigation.txt` | `i_Investigation.txt` | `.txt` | 9,739 | 0.0093 | 2026-11-14 14:05:46 | No | Readable plain-text metadata export |
| `PSI-98_metadata_PSI-166_SAFFIRE-I\s_PSI-98.txt` | `s_PSI-98.txt` | `.txt` | 56 | 0.0001 | 2026-11-14 14:05:46 | No | Readable tab-delimited placeholder |
| `SAME EIRD Rev 2.00 02-25-05 HIgh Q.pdf` | `SAME EIRD Rev 2.00 02-25-05 HIgh Q.pdf` | `.pdf` | 5,378,409 | 5.1304 | 2026-11-14 13:51:46 | No | PDF header `%PDF-1.4` and `%%EOF` marker present; text not extracted |

**Totals:** 9 files; 8 TXT (52,872 bytes); 1 PDF (5,378,409 bytes); 5,431,281 bytes total. No file has zero bytes. No archive-format file or unexpected extension was found. The four `s_PSI-*.txt` files have matching SHA-256 values and identical bytes. TXT records were readable. The PDF has basic recognizable structural markers, but a full parser-based corruption/readability check was unavailable; do not treat these markers as proof the entire PDF is intact.

## 4. File Format Distribution

| Extension / type | Files | Total bytes | Assessment |
|---|---:|---:|---|
| `.txt` | 8 | 52,872 | Four investigation metadata exports and four duplicate placeholder sample tables |
| `.pdf` | 1 | 5,378,409 | One NASA-listed engineering document; body unavailable to local text inspection |
| Archives | 0 | 0 | No ZIP, 7z, RAR, or other archive was present in the recursive file inventory |
| Other / unexpected | 0 | 0 | None found |

## 5. Investigation-wise Metadata Analysis

In each local export, the formal `INVESTIGATION` fields (`Investigation Identifier`, `Investigation Title`, `Investigation Description`) are blank. The populated identity fields occur under `STUDY` as `Study Identifier` and `Study Title`. Therefore the report uses the populated study identifiers, corroborated against NASA PSI records, and does not infer a different identifier from folder-name fragments. The folder suffixes (`PSI-176`, `NEWID-7`, `PSI-133`, `PSI-166`) are not asserted to be authoritative investigation identifiers; their meaning is not established by these exports.

### PSI-107 — Smoke Point In Co-flow Experiment (SPICE)

- **Local evidence:** `PSI-107_metadata_PSI-176_SPICE\i_Investigation.txt`, `STUDY` and `STUDY CONTACTS`; `Study Identifier PSI-107`, title `Smoke Point In Co-flow Experiment`, acronym SPICE, investigation DOI `10.60555/9kbh-e962`, release/submission date 18-Sep-2024. The `Investigation` identifier/title/description fields are blank. Local `Comment[Data Source Accession]` and `Comment[Data Source Link]` are blank. Start/end date fields are blank.
- **Description/objectives:** The local export's `Comment[Objective]` describes microgravity and analogous ground experiments, smoke-point properties of non-buoyant jet diffusion flames, effects of burner diameter and co-flow, fuel sooting propensity, luminous flame shape/residence time, and air/fuel flow effects. `Comment[Hypothesis]` and `Comment[Approach]` describe the motivation and conditions.
- **Conditions/variables described (not locally measured):** fuels listed include methane, ethylene, propane, propylene, and propylene mixtures; burner diameters 0.41, 0.76, and 1.6 mm; co-flow 5.4–65 cm/s; 526 flames; flame lengths/height, radiative heat losses, and co-flow air velocity distributions. Source: local `Comment[Approach]`.
- **PI:** David Urban (NASA GRC), with Peter Sunderland (University of Maryland) listed as Co-I; local `STUDY CONTACTS` fields.
- **Publications:** Local `STUDY PUBLICATIONS` lists multiple publications, including *Laminar Smoke Points in Coflow Measured Aboard the International Space Station*, DOI `10.2514/6.2010-1105`, plus other listed titles and DOI values. These are references, not embedded papers or datasets.
- **License:** Not found in the local export. The official record displays CC0-1.0 online; this is online-verified, not locally recorded.
- **Status:** **VERIFIED** for study identity and documented description; **NOT FOUND** for measurements in the local files.

### PSI-62 — Concurrent Flame Spread Modeling using Flamelet Generated Manifolds in Microgravity with Comparison to BASS Experiments using Two-Color Tomography

- **Local evidence:** `PSI-62_metadata_NEWID-7_Concurrent Flame Spr\i_Investigation.txt`, `STUDY` and `STUDY CONTACTS`; `Study Identifier PSI-62`, exact title above, DOI `10.60555/e9xp-ex83`, submission 30-Apr-2021, public release 14-Nov-2025. The formal `Investigation` identity fields are blank. `Comment[Data Source Accession]` and `Comment[Data Source Link]` are blank. Acronym and hardware/platform fields are blank.
- **Description/objectives:** Local `Comment[Objective]` and `Comment[Approach]` describe UFGM modeling of concurrent flame spread, coupled fluid/solid response, charring/ablation, PMMA and wax test geometries, and comparison with BASS/BASS-II imagery and simulations. This is a ground-investigation/modeling research record; it is not itself a measurement table.
- **Variables/metrics described (not locally measured):** flame geometry, temperature distribution, soot volume fraction, flame-spread rate, and two-color reconstructed soot/temperature fields; local `Comment[Approach]`.
- **PI:** Paul DesJardin; David Urban listed as Project Scientist; affiliations and roles in local `STUDY CONTACTS`.
- **Publications:** Local `STUDY PUBLICATIONS` includes *Microgravity flammability boundary for PMMA rods in axial stagnation flow: Experimental results and energy balance analyses* (DOI `10.1016/j.combustflame.2017.03.001`) and three modeling/diagnostic publications with DOI values.
- **License:** Not found locally; official PSI record displays CC0-1.0 online.
- **Status:** **VERIFIED** for study identity and documented modeling scope; **NOT FOUND** for measurement values in the local files.

### PSI-69 — Flame Extinguishment Experiment (FLEX)

- **Local evidence:** `PSI-69_metadata_PSI-133_FLEX\i_Investigation.txt`, `STUDY` and `STUDY CONTACTS`; `Study Identifier PSI-69`, title `Flame Extinguishment Experiment`, acronym FLEX, DOI `10.60555/mbq8-0451`, submission/release 31-Jul-2016, dates 01-Aug-2007 through 31-Jul-2016. Formal `Investigation` identity fields are blank. Local data-source accession/link fields are blank.
- **Description/objectives:** Local `Comment[Objective]` documents liquid-fuel flammability limits, gaseous suppressants (CO2, He, SF6), reduced-gravity combustion modeling, droplet burning and extinction, radiation, soot, and temperature profiles.
- **Conditions/hardware:** Local `Comment[Experiment Hardware]` identifies CIR/FCF and MDCA; `Comment[Flight Platform]` identifies ISS. The approach describes large droplet combustion, ambient pressure and oxygen, and suppressant effects.
- **Variables described (not locally measured):** droplet burning rates/diameters, flame extinction, heat radiation, soot, temperature, ambient pressure/oxygen and suppressant conditions; these are metadata statements in `Comment[Objective]` and `Comment[Approach]`.
- **PI:** Forman Williams; Daniel Dietrich is listed as Project Scientist; multiple Co-Is are listed in `STUDY CONTACTS`.
- **Publications:** Local `STUDY PUBLICATIONS` includes *Droplet Combustion Experiments Aboard the International Space Station* (DOI `10.1007/s12217-014-9372-2`), *Methanol Droplet Extinction in Oxygen/Carbon-dioxide/Nitrogen Mixtures in Microgravity: Results from the International Space Station Experiments*, and other listed papers.
- **License:** Not found locally; official PSI record displays CC0-1.0 online.
- **Status:** **VERIFIED** for study identity and described science; **NOT FOUND** for measurements in the local files.

### PSI-98 — Spacecraft Fire Safety Experiment-I (SAFFIRE-I)

- **Local evidence:** `PSI-98_metadata_PSI-166_SAFFIRE-I\i_Investigation.txt`, `STUDY` and `STUDY CONTACTS`; `Study Identifier PSI-98`, title `Spacecraft Fire Safety Experiment-I`, acronym SAFFIRE-I, DOI `10.60555/0t15-1z43`, submission/release 18-Sep-2024, dates 02-Mar-2001 through 28-Feb-2008. Formal `Investigation` identity fields are blank. Local data-source accession/link fields are blank.
- **Description/conditions:** Local `Comment[Approach]` states the experiment was performed aboard a Cygnus resupply vehicle after it departed ISS, used a 0.94 m by 0.4 m Sibal cotton/fiberglass sample (75% cotton, 25% fiberglass by weight), and ran at 20 cm/s air flow. These are metadata-reported conditions, not measurements present in the downloaded files.
- **Variables/instrumentation described (not locally measured):** thermocouple flow/flame/plume temperatures, radiometer flame radiation, pressure, CO2 and O2 mole fraction, flow velocity from anemometers, and flame imagery from two cameras; local `Comment[Approach]`. The metadata says recorded data were compressed and downlinked.
- **PI:** David Urban (NASA GRC), local `STUDY CONTACTS`.
- **Publications:** Local `STUDY PUBLICATIONS` includes *Flame spread: Effects of microgravity and scale* (DOI `10.1016/j.combustflame.2018.10.012`), *Transient flame growth and spread processes over a large solid fabric in concurrent low-speed flows in microgravity – Model versus experiment* (DOI `10.1016/j.proci.2018.05.168`), and other titles.
- **License:** Not found locally; official PSI record displays CC0-1.0 online.
- **Status:** **VERIFIED** for study identity and measurement/instrument descriptions; **NOT FOUND** for measurements in the local files.

## 6. Empty and Incomplete Files

**VERIFIED:** None of the four `s_PSI-*.txt` files is zero bytes, whitespace-only, or unreadable. Each is exactly 56 bytes and contains the same two-line tab-separated text:

```text
Source Name    Sample Name
Do not use this    Do not use this
```

The second line is explicitly a placeholder. All four have the same SHA-256 (`CB9374159B9B01A83BFE53A0B8BA1A602793DF86F298E0AD222615C55D200135`). These are **incomplete/non-data placeholder exports**, not empty files and not sample tables. The exact bytes are plain ASCII text with tabs/newlines; there is no hidden content revealed by the byte-level check.

The `i_Investigation.txt` files are readable, but their formal Investigation identity/description fields and the local `Data Source Accession` / `Data Source Link` fields are blank. Their populated `Study` records contain useful metadata, but the paired sample tables are unusable placeholders.

## 7. SAME EIRD PDF Analysis

- **Local file:** `SAME EIRD Rev 2.00 02-25-05 HIgh Q.pdf` (5,378,409 bytes).
- **Integrity/access:** **PARTIALLY VERIFIED.** The header is `%PDF-1.4` and the file ends with `%%EOF`, but no installed PDF library or extractor was available to parse pages, extract text, or check internal object/page integrity. No OCR was used. Page count and whether text extraction would be complete are unknown.
- **NASA classification:** **VERIFIED online, not from local PDF contents.** The official PSI-101 record (SAME-R) lists this exact filename under **Engineering Documents** in its version history. This supports classifying the file as a NASA-listed engineering document. It does not expose the PDF body in this inspection.
- **Content fields:** Document title beyond filename, document number, revision, publication date, author/organization, abstract/introduction, table of contents, objectives, experimental requirements, instrumentation, measured variables, units, references, and cited sources are **NOT ACCESSIBLE** from the local PDF in this environment. The strings `Rev 2.00` and `02-25-05` appear in the filename only; they are not independently validated as document metadata. The title term `EIRD` is not expanded because its meaning was not established from inspected text.
- **Document type:** **PARTIALLY VERIFIED — engineering document** based on NASA PSI-101's online file category. It is not supported as an experimental dataset, research publication, or source of measurements by the available inspection evidence. Its specific requirements/content remain unverified.

## 8. NASA Source and Provenance Analysis

Online checks were made against the supplied official NASA PSI URLs. This verification is separate from the local evidence: the local exports carry a `Term Source File` reference to PSI and populated study IDs, while their data-source accession/link fields are blank. The official pages corroborate the study identity and record-level descriptions; they do not prove that the local placeholders contain data.

| Local folder / file | Local populated Study Identifier | Online official PSI record | Provenance assessment |
|---|---|---|---|
| `PSI-107_metadata_PSI-176_SPICE` | PSI-107 | [NASA PSI-107](https://psi.nasa.gov/physci/repo/data/investigations/PSI-107) | **VERIFIED** as SPICE record by study ID/title. Folder token `PSI-176` is not established as its authoritative record ID. |
| `PSI-62_metadata_NEWID-7_Concurrent Flame Spr` | PSI-62 | [NASA PSI-62](https://psi.nasa.gov/physci/repo/data/investigations/PSI-62) | **VERIFIED** as PSI-62 study record. `NEWID-7` meaning is not established. |
| `PSI-69_metadata_PSI-133_FLEX` | PSI-69 | [NASA PSI-69](https://psi.nasa.gov/physci/repo/data/investigations/PSI-69) | **VERIFIED** as FLEX record. Folder token `PSI-133` is not established as authoritative. |
| `PSI-98_metadata_PSI-166_SAFFIRE-I` | PSI-98 | [NASA PSI-98](https://psi.nasa.gov/physci/repo/data/investigations/PSI-98) | **VERIFIED** as SAFFIRE-I record. Folder token `PSI-166` is not established as authoritative. |
| `SAME EIRD Rev 2.00 02-25-05 HIgh Q.pdf` | No local investigation metadata file | [NASA PSI-101 (SAME-R)](https://psi.nasa.gov/physci/repo/data/investigations/PSI-101) | **PARTIALLY VERIFIED**: NASA PSI-101 version history lists the exact filename under Engineering Documents. Local PDF content was not extracted; the local directory alone does not establish its download origin. |

The PSI-101 web record identifies SAME-R as “Smoke Aerosol Measurement Experiment-Reflight” and places the exact EIRD filename in its Engineering Documents section/version history. This is online provenance support for the PDF's association with the PSI-101 record, not proof of its internal contents or a checksum-level identity with a NASA-hosted file.

## 9. Scientific Variables Identified

The following are variables/conditions **described by metadata or official web-page text**. No corresponding numerical measurement values were found in the local files.

| Investigation | Variables or conditions described | Evidence location |
|---|---|---|
| PSI-107 SPICE | Fuel identity; burner diameter; co-flow velocity; fuel flow; flame length/height; smoke point/sooting; radiative heat loss; air-velocity distribution; 526 flames reported | Local `i_Investigation.txt`, `Comment[Approach]` and `Comment[Objective]` |
| PSI-62 modeling/BASS comparison | PMMA/wax sample geometries; temperature distribution; soot volume fraction; flame geometry; flame-spread rate; two-color tomography reconstructions | Local `i_Investigation.txt`, `Comment[Approach]` and `Comment[Objective]` |
| PSI-69 FLEX | Liquid fuel/droplet conditions; ambient pressure and oxygen; suppressant identities CO2/He/SF6; burning rate; extinction; radiative heat; soot; temperature | Local `i_Investigation.txt`, `Comment[Objective]` and `Comment[Approach]` |
| PSI-98 SAFFIRE-I | Flow/flame/plume temperature; pressure; CO2 and O2 mole fraction; airflow velocity; radiation; flame images; sample dimensions/composition | Local `i_Investigation.txt`, `Comment[Approach]` |
| PSI-101 SAME-R / EIRD | No variables can be confirmed from the inaccessible local PDF. SAME-R subject and data categories are visible on the official PSI web record, but are not measurement values in this directory. | NASA PSI-101 page; local PDF body inaccessible |

**Units explicitly present in local metadata:** PSI-107 burner diameters (mm) and co-flow (cm/s); PSI-98 air flow velocity (cm/s) and sample dimensions (m). Other variables/conditions above do not have units supplied in the cited local passages. Do not assume units for them. The PDF's units and instrumentation are **NOT ACCESSIBLE**.

## 10. Availability of Actual Experimental Measurements

**VERIFIED — no genuine numerical experimental measurement table or time series is present among these 9 local files.** The only candidate tabular files are the four `s_PSI-*.txt` placeholders and each says “Do not use this.” The four other TXT files are metadata exports. The PDF is not text-inspectable here and is categorized by NASA as an Engineering Document, not as raw or analyzed data.

| Requested data type | Finding in local directory |
|---|---|
| Numerical observations / CSV / TSV | **NOT FOUND.** No CSV/TSV file; the four TSV-like TXT files are placeholder text. |
| Time-series data | **NOT FOUND.** |
| Temperature values | **NOT FOUND.** SAFFIRE-I metadata describes thermocouples and temperature measurement, but no readings. |
| Oxygen / carbon dioxide values | **NOT FOUND.** SAFFIRE-I metadata describes sensors, but no readings. |
| Pressure / airflow values | **NOT FOUND.** Metadata describes instrumentation or conditions, but no data series. |
| Flame / smoke particle observations | **NOT FOUND.** Metadata describes cameras, flame variables, and smoke studies, but no local images, particle observations, or numeric arrays. |
| Fuel properties / sample conditions | **PARTIALLY VERIFIED** as descriptive metadata only; no dataset rows or complete experimental-condition table locally. |
| Scientific units | **PARTIALLY VERIFIED** for the few units explicitly stated in metadata; no units attached to observation data because none is present. |

## 11. Dataset Quality and Limitations

- **Metadata integrity:** Four readable exports have detailed objectives, approach, investigator/publication metadata, and selected conditions. They are useful as catalogue records, not data files.
- **Identifier hygiene:** The `Study Identifier` values are the defensible PSI record IDs. The higher-level `INVESTIGATION` fields are blank; folder-name tokens are not accepted as replacements.
- **Placeholder files:** Four byte-identical files represent an export/data retrieval failure or placeholder state. They must not be ingested as measurements.
- **Coverage:** The local directory does not include raw, analyzed, or published numerical datasets for any of the four investigations. Metadata mention values and instruments but not the observations.
- **PDF limitation:** Basic PDF markers were checked but no parser was available. Content, page count, metadata, and full structural integrity remain unknown.
- **Online-vs-local boundary:** Online PSI descriptions and file-category listings help identify official records and likely data locations; they do not mean those data have been downloaded locally or independently validated.
- **No licensing assumption:** Local files do not state a license. Online PSI records show CC0-1.0 for the four investigation records; verify the terms attached to each specific downloaded artifact before redistribution/use.

## 12. Missing Data and Additional Download Requirements

1. **SAFFIRE-I:** Obtain measurement products from the PSI-98 official record, especially the **Raw Data** category and relevant supporting **Science Documents** / **Engineering Documents**. Select products that contain actual synchronized sensor time series (temperature, pressure, O2, CO2, flow), radiometry, and/or video, and acquire their readme, calibration, unit, channel, and timing documentation. The local metadata describes these channels but contains none of their values.
2. **SAME-R / PSI-101:** Obtain selected **Analyzed Data** and **Raw Data** products from the PSI-101 record, with file-level readmes and the official report `PSI-101_Reports_SAME-R_Final Report.pdf` where useful. The exact local EIRD file is categorized as Engineering Documents; do not treat it as data. SAME-R is a strong complementary resource for smoke aerosol size/transport questions.
3. **SPICE / PSI-107:** Obtain raw/processed flame-imaging or experimental-table products and their readmes from the PSI-107 record if smoke-point/soot behavior is part of the MVP. Metadata describes 526 flames but provides no measurement rows locally.
4. **FLEX / PSI-69:** Obtain selected raw/processed droplet-combustion observations, experimental tables, and readmes from the PSI-69 record if droplet extinction/suppressant analytics are in scope.
5. **PSI-62:** Download model output/validation or BASS/BASS-II data only if the product needs flame-spread modeling. The local PSI-62 record describes research methods and metrics, not measurement data; establish whether the needed imagery or validation data belong to this PSI project or the referenced BASS investigations before selecting files.

These are acquisition requirements, not completed downloads. No additional files were downloaded during this inspection. At acquisition, record each original NASA URL, record/file identifier, version, license, checksum, unit definitions, calibration, time basis, and data dictionary. Do not use a file solely because its name appears relevant.

## 13. Dataset Readiness Assessment

**Status: NOT READY for scientific analytics on experimental observations.**

| Readiness criterion | Status | Basis |
|---|---|---|
| Investigation/catalogue metadata | **VERIFIED** | Four readable study metadata exports; PSI IDs/titles corroborated online |
| Original source association | **PARTIALLY VERIFIED** | Official PSI records match the four study IDs; local data-source fields are blank |
| Actual experimental measurements present | **NOT FOUND** | No numeric tables/time-series/images; sample tables are placeholders |
| PDF scientific content available | **NOT ACCESSIBLE** | No existing extraction tool; OCR and installation were prohibited |
| Units/calibration/data dictionary for observations | **NOT FOUND** | No observation files or local measurement documentation |
| Research catalogue / MVP metadata prototype | **VERIFIED as feasible** | Local records support a provenance-aware catalogue with explicit gaps |
| Scientific modeling/training/benchmarking from local measurements | **NOT READY** | Measurements must first be obtained and validated |

It is reasonable to begin a **metadata catalogue** and a documented ingestion plan now. Do not train, validate, or present analytics as NASA-derived experimental results until real, traceable measurement files are acquired and quality-checked.

## 14. Recommended Next Actions

1. **MVP priority: SAFFIRE-I / PSI-98.** Its record is directly aligned to spacecraft fire safety and describes complementary physical measurements (temperature, pressure, O2/CO2, airflow, radiation, flame video). This supports an interpretable fire-state insight use case better than a measurement-free folder. Download suitable raw data and its documentation before implementation of scientific analytics.
2. **Second resource: SAME-R / PSI-101.** Add analyzed smoke aerosol products for particle-size/transport and detector-relevance research; use the PSI-101 official record to choose actual data products, not the EIRD filename.
3. **Additional focused resources:** PSI-107 for co-flow smoke-point flame behavior; PSI-69 for droplet combustion/extinction/suppressant research. Keep PSI-62 as a modeling/validation track unless its actual downloadable products match the intended MVP.
4. **Useful current local files:** all four `i_Investigation.txt` files can seed an investigation catalogue and bibliographic/provenance index. The official NASA record links in Section 8 are the authoritative starting points for file selection.
5. **Incomplete local files:** all four `s_PSI-*.txt` files are placeholder templates; exclude them from analytics and mark them as failed/incomplete exports in any ingest log. The PDF is useful as a NASA-listed engineering-document lead but not yet as an understood technical source.
6. **Preserve as original raw sources:** retain all 9 files byte-for-byte, including placeholders and the PDF, with the checksums in Section 15. Preserve acquisition timestamps and original directory names. Do not silently replace the placeholder files; record any future NASA downloads as separate, provenance-linked artifacts.
7. **Research catalogue:** catalogue the four metadata records now, preserving exact PSI study IDs, title, source URL, blank local data-source fields, references, and the distinction between described variables and available observations. Record the PDF as “PSI-101 Engineering Documents association; body not inspected.”
8. **Analytics gate:** acquire genuine NASA raw/analyzed measurement products first; then document formats, time/channel alignment, units, calibration, missingness, quality flags, experimental conditions, and license. Only then assess suitable features and analysis methods.

## 15. Detailed File Checksum Manifest

SHA-256 was computed from every local file using PowerShell `Get-FileHash -Algorithm SHA256`. Relative paths are rooted at `D:\DATASETS 2`.

| Relative path | Bytes | SHA-256 |
|---|---:|---|
| `PSI-107_metadata_PSI-176_SPICE\i_Investigation.txt` | 9,019 | `2DE0B5489BA8ABE994DCF73F202563F4F2B255C1A285183062520B74F948C464` |
| `PSI-107_metadata_PSI-176_SPICE\s_PSI-107.txt` | 56 | `CB9374159B9B01A83BFE53A0B8BA1A602793DF86F298E0AD222615C55D200135` |
| `PSI-62_metadata_NEWID-7_Concurrent Flame Spr\i_Investigation.txt` | 9,402 | `FBBE3E34F381692C62721F4D59A6E85121E90CAC852A5846A885DA8935EDAA16` |
| `PSI-62_metadata_NEWID-7_Concurrent Flame Spr\s_PSI-62.txt` | 56 | `CB9374159B9B01A83BFE53A0B8BA1A602793DF86F298E0AD222615C55D200135` |
| `PSI-69_metadata_PSI-133_FLEX\i_Investigation.txt` | 24,488 | `F425BF49ED355CC4941E5F6DDE215D477F084834BD9A4BF77E8BF231CD9A7520` |
| `PSI-69_metadata_PSI-133_FLEX\s_PSI-69.txt` | 56 | `CB9374159B9B01A83BFE53A0B8BA1A602793DF86F298E0AD222615C55D200135` |
| `PSI-98_metadata_PSI-166_SAFFIRE-I\i_Investigation.txt` | 9,739 | `26C269438B45A3C8C281F66D1BEEC07678CDD86755E1E6401B66AEAE60FE0C1D` |
| `PSI-98_metadata_PSI-166_SAFFIRE-I\s_PSI-98.txt` | 56 | `CB9374159B9B01A83BFE53A0B8BA1A602793DF86F298E0AD222615C55D200135` |
| `SAME EIRD Rev 2.00 02-25-05 HIgh Q.pdf` | 5,378,409 | `941DCA3CCF7132913BFD73E8A408F3EA558EAA822486DD53FFCDFA26127461CB` |

**Manifest status: VERIFIED** for filenames, byte counts, timestamps, and checksums captured during this inspection. Hashes identify the inspected local bytes; they do not independently establish NASA-hosted file identity.