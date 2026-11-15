# Phase 2 — Dataset Discovery, Ingestion & Quality Assessment

**Project:** FIRELYTICS AI — Flame in Freefall  
**Inspection date:** 2026-11-15  
**Status:** Phase 2 complete; no Phase 3 model training has started.

## 1. Scope and provenance policy

This report distinguishes local raw telemetry, reconciled archival products, catalogue condition envelopes, and unavailable external raw data. No NASA data was downloaded for this phase, and no dataset is described as local unless a file was found in the repository.

The repeatable inventory and per-column quality calculations are exposed by `GET /ml/datasets` and `GET /api/ml/datasets`. It inspects the local PSI-101 run CSVs, all CSVs in both metadata folders, the backend catalogue JSON, and the quarantine files. The response includes source-relative paths, SHA-256, schemas, inferred units, record counts, blank/sentinel counts and percentages, run groupings, categorical distributions, and deployment availability. The current inventory contains 14 Tier-1 catalogue records, 10 Tier-2 scope records, seven raw run CSVs (10,350 rows), two quarantined duplicate CSVs, nine backend metadata CSVs, and 50 workspace metadata CSVs.

The backend deployment packages `backend/data/catalogue/` and `backend/data/metadata/`; it does not package root `data/raw/` or root `data/metadata/`. Local file presence is not permission to redistribute. The DataCite record for PSI-101 identifies CC0-1.0 rights for record metadata; this repository does not establish a separate license for each raw instrument CSV. Cite NASA PSI and the investigators, preserve the original file/run/row provenance, and check individual file terms before redistribution.

## 2. DataCite and NASA PSI catalogue audit

The 14 Tier-1 records are investigation metadata and condition envelopes, not 14 local experiment tables. For all 14, `o2_range_pct`, `pressure_range_psi`, `hardware_rack`, `fuel_phase`, `gravity_regimes`, and `research_area` are populated in the local catalogue; `airflow_range_cm_s` is populated for 12. The ten Tier-2 entries are repository-scope context, not independent tabular experiments.

DOIs were checked against the DataCite REST API on the inspection date. Twelve identifiers resolved to matching DataCite records; the PSI-20 identifier returned HTTP 404, and PSI-22 has no DOI in the local catalogue.

| PSI ID | Investigation | Catalogue DOI | DataCite check |
|---|---|---|---|
| PSI-101 | SAME-R | `10.60555/2np7-jv14` | Verified |
| PSI-102 | SAME | `10.60555/gd4k-8h62` | Verified |
| PSI-47 | DAFT / DAFT-2 | `10.60555/ztgj-d202` | Verified |
| PSI-26 | BASS | `10.60555/58h4-dy80` | Verified |
| PSI-25 | BASS-II | `10.60555/4qc4-de67` | Verified |
| PSI-98 | SAFFIRE-I | `10.60555/0t15-1z43` | Verified |
| PSI-99 | SAFFIRE-II/III | `10.60555/2chp-m469` | Verified |
| PSI-20 | BRE | `10.60555/vb93-3y72` | DataCite returned 404; not treated as verified |
| PSI-159 | CFI-G | `10.60555/cyt1-kh64` | Verified |
| PSI-22 | E-FIELD | Pending in local catalogue | No DOI to check |
| PSI-69 | FLEX | `10.60555/mbq8-0451` | Verified |
| PSI-68 | FLEX-2/CFI | `10.60555/byp8-h018` | Verified |
| PSI-107 | SPICE | `10.60555/9kbh-e962` | Verified |
| PSI-106 | SLICE | `10.60555/pm12-rg61` | Verified |

The prompt-suggested PSI-101 DOI `10.60555/037m-9382` returned HTTP 404 from DataCite. The verified PSI-101 DOI is the catalogue value `10.60555/2np7-jv14`. Verification sources are the [DataCite DOI API](https://api.datacite.org/dois/) and the [NASA PSI-101 record](https://psi.nasa.gov/physci/repo/data/investigations/PSI-101). PSI-20's DataCite 404 is a verification result as of the inspection date, not proof that no other identifier or later record exists.

PSI-101's catalogue metadata describes Pyrell® intumescent fire-retardant foam among the SAME-R sample set, ISS / Microgravity Science Glovebox, approximately 21% O₂ and 14.7 psi cabin conditions, and 0–5 cm/s residual flow. These are investigation-level descriptions; they do not establish per-row settings for each local raw run.

## 3. Locally present PSI-101 raw data

Seven direct `Run_NNN` directories contain a 98-column CSV each. Together they contain **10,350 rows**. The `RunID` used for grouping is inferred from the parent directory because it is not a raw CSV column. The raw sample timestamps have a one-second median interval, with duplicate timestamps and occasional longer gaps; they are not an exactly regular sequence.

| Run | File | Rows | P-Trak `-999` sentinel count | Timestamp notes |
|---:|---|---:|---:|---|
| 63 | `Run_063/HKPData_gmt235_1.csv` | 1,236 | 22 | Four duplicate timestamp groups |
| 64 | `Run_064/HKPData_gmt235_3.csv` | 1,688 | 6 | Three duplicate timestamp groups |
| 76 | `Run_076/HKPData_gmt238_4.csv` | 1,427 | 7 | Three duplicate timestamp groups |
| 84 | `Run_084/HKPData_gmt242_1.csv` | 1,556 | 376 | 35 duplicate timestamp groups |
| 87 | `Run_087/HKPData_gmt242_3.csv` | 751 | 9 | Two duplicate timestamp groups |
| 95 | `Run_095/HKPData_gmt250_4.csv` | 1,891 | 197 | 22 duplicate groups; one 615 s adjacent timestamp gap |
| 97 | `Run_097/HKPData_gmt251_1.csv` | 1,801 | 0 | One 128 s adjacent timestamp gap |
| **Total** | **7 CSV files** | **10,350** | **617** | Median adjacent interval: **1 s** |

No blank cells were observed in the seven raw CSVs. All 617 `-999` sentinels occur in `PTrakMeasurement(PtPerCC)` (5.96% of the 10,350 P-Trak cells); mask them as missing, not as measured zero or a particle count. The other inspected raw channels have no blank or `-999` cells.

The exact sensor/source headers are available in the registry schema for each raw file. Their unit-bearing channel families include:

| Measurement family | Exact source columns / units |
|---|---|
| Time / cycle | `Time` (s epoch), `TimeString`, `ElapsedTestTime(Secs)` (s), `CycleCounter` (cycle index) |
| Aerosol mass | `DustTrakAMeasurement(MgPerM3)`, `DustTrakBMeasurement(MgPerM3)` (mg/m³) |
| Aerosol number | `PTrakMeasurement(PtPerCC)` (particles/cm³) |
| Analog / detector signals | `DustTrakAAnalogMeasurement(Volts)`, `DustTrakBAnalogMeasurement(Volts)`, `PTrakPowerMeasurement(Volts)`, `ISSDetectorObscurationMeasurement(Volts)`, `ISSDetectorScatterMeasurement(Volts)`, `STSDetectorMeasurement(Volts)`, `IonDetectorAMeasurement(Volts)`, `IonDetectorBMeasurement(Volts)` (V) |
| Temperature / resistance | `GasPlumeTemperature(DegC)`, `MFCTemperature(DegC)` (°C); `SampleResistance(Ohms)` (Ω) |
| Flow | `LFEFlowRate[AT08](SCCM)` (sccm); `MFCMassFlowRate(LPM)`, `MFCAnalogSetpoint[BN19](LPM)`, `MFCAnalogFlowRate(LPM)` (L/min) |
| Pressure | `MFCPressure(PSIA)`, `GN2MainPressure[PN02](PSIA)`, `VacuumPressure[VR04](PSIA)`, `DriveSidePressure[BN02](PSIA)`, `SampleSidePressure[AT20](PSIA)` (psia); `GN2RegulatedPressure[PN12](PSIG)` (psig) |

The raw headers do not contain a cm/s airflow sensor channel or a kPa pressure channel. Such units must not be assigned to these columns by assumption.

`Run_087` is present locally but is not part of the six-run production reconciliation. Its inspection row reports 751 total rows, 727 with `TestNumber=87`, and 716 with `RunMode=3`; `DustTrakAState` is 0 for 750 rows and 8 for one row, while `DustTrakAPower` is 0 for all 751. The historical eligibility gate requires `DustTrakAState=6` and `DustTrakAPower=1`, so this file contributes no eligible DustTrak-A rows under that gate. It is not silently added to the validated archive.

The two CSVs under `data/raw/PSI-101/_quarantine/` have SHA-256 hashes identical to Runs 95 and 97 respectively. Their “Run107” directory names are candidate labels, not two additional independent experiments, and they are excluded from the raw-run count. `Run_052` is represented by a PDF, `Run_071` and `Run_074` by PPTX files, and `Reports/Archived/SAMER_Final_0602_2014_archived.pdf` is a document, not a row-level measurement table.

## 4. Reconciled PSI-101 cycle and metadata products

The production backend's `backend/data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv` contains **7,900 cycle records** across the six validated groups. Its exact schema is:

`RunID`, `Cycle`, `RelativeCyclePhase`, `ExpectedBand`, `ObservedBand`, `ExceptionIndicator`, `SourceRowCount`, `MixedBandIndicator`, `DuplicateCycleIndicator`, `DuplicateRowCount`, `SourceDataRows`, `FirstTimestamp`, `LastTimestamp`, `FirstTimestampSeconds`, `LastTimestampSeconds`, `ClassifiedBandCount`.

| RunID | Cycle rows | Exception 0 | Exception 1 | Unlabeled mixed cycles |
|---:|---:|---:|---:|---:|
| 63 | 1,227 | 1,215 | 8 | 4 |
| 64 | 1,505 | 1,498 | 6 | 1 |
| 76 | 1,264 | 1,260 | 2 | 2 |
| 84 | 1,264 | 1,077 | 185 | 2 |
| 95 | 1,317 | 1,219 | 96 | 2 |
| 97 | 1,323 | 1,320 | 0 | 3 |
| **Total** | **7,900** | **7,589** | **297** | **14** |

The 14 `MixedBand` cycles have blank `ExceptionIndicator` and are excluded from the binary target, leaving 7,886 labeled cycles. Of the 7,900 cycle rows, 25 have `DuplicateCycleIndicator=1`. `ObservedBand` counts are 3,940 `20000+`, 3,946 `10000-14999`, and 14 `MixedBand`; `ExpectedBand` counts are 3,950 in each of the two binary bands. These are reconciled derived labels, not independent fire, ignition, extinction, or smoke-versus-dust outcomes.

The backend bundle contains nine CSV products:

| Backend metadata file | Rows × columns |
|---|---:|
| `ArchivedExceptionCycleIDs.csv` | 297 × 3 |
| `MixedCycleIDs.csv` | 14 × 2 |
| `MixedCycleSourceRowRefs.csv` | 38 × 3 |
| `PSI101_Pyrell_DustTrakA_PhaseSummary_2026-11-14_170034.csv` | 12 × 16 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv` | 7,900 × 16 |
| `PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_20261114_181648.csv` | 101 × 11 |
| `PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_181648.csv` | 240 × 4 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_181648.csv` | 66 × 24 |
| `PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_181648.csv` | 6 × 34 |

The backend `RunMetrics` table provides one row per run; `LagCorrelation` has 40 lags per run. These are archived analyses. The backend archive loader validates those products and explicitly does **not** replay raw source CSVs. The separate workspace `data/metadata/` contains 50 CSV artifacts and five text audit reports; its inventory includes the later `20261114_183947` cycle/periodicity snapshot, phase and exception summaries, row/cycle lineage audits, Run-87 diagnostics, and phase-reversal/episode-control analyses. The API returns exact row counts, source columns, per-column missingness, class distributions, and grouping for each of those 50 files.

The complete inspected workspace CSV inventory is:

| `data/metadata/` file | Rows × columns |
|---|---:|
| `HKPData_inventory_2026-11-14.csv` | 18 × 10 |
| `PSI101_Pyrell_Column_Profile_2026-11-14.csv` | 686 × 13 |
| `PSI101_Pyrell_Duplicate_Timestamp_Audit_2026-11-14.csv` | 69 × 8 |
| `PSI101_Pyrell_DustTrakA_AnalogTransitions_2026-11-14.csv` | 7,868 × 11 |
| `PSI101_Pyrell_DustTrakA_Cycle_Bands_2026-11-14.csv` | 12 × 10 |
| `PSI101_Pyrell_DustTrakA_Cycle_Sequence_2026-11-14.csv` | 6 × 6 |
| `PSI101_Pyrell_DustTrakA_DuplicateCycles_2026-11-14.csv` | 25 × 9 |
| `PSI101_Pyrell_DustTrakA_ExceptionClusters_2026-11-14_170034.csv` | 68 × 5 |
| `PSI101_Pyrell_DustTrakA_ExceptionWindows_2026-11-14_170034.csv` | 166 × 8 |
| `PSI101_Pyrell_DustTrakA_MixedBand_CycleSummary_2026-11-14_170034.csv` | 14 × 13 |
| `PSI101_Pyrell_DustTrakA_MixedBand_OriginalRows_2026-11-14_170034.csv` | 38 × 106 |
| `PSI101_Pyrell_DustTrakA_ParityBand_Cycles_2026-11-14.csv` | 32 × 6 |
| `PSI101_Pyrell_DustTrakA_ParityBand_Rows_2026-11-14.csv` | 24 × 8 |
| `PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_20261114_181648.csv` | 101 × 11 |
| `PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_20261114_183947.csv` | 101 × 11 |
| `PSI101_Pyrell_DustTrakA_Periodicity_BoundaryRows_20261114_181648.csv` | 80 × 19 |
| `PSI101_Pyrell_DustTrakA_Periodicity_BoundaryRows_20261114_183947.csv` | 80 × 19 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_181648.csv` | 66 × 24 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_183947.csv` | 66 × 24 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv` | 7,900 × 16 |
| `PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_183947.csv` | 7,900 × 16 |
| `PSI101_Pyrell_DustTrakA_Periodicity_ExcludedCycles_20261114_181648.csv` | 51 × 6 |
| `PSI101_Pyrell_DustTrakA_Periodicity_ExcludedCycles_20261114_183947.csv` | 51 × 6 |
| `PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_181648.csv` | 240 × 4 |
| `PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_183947.csv` | 240 × 4 |
| `PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_181648.csv` | 6 × 34 |
| `PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_183947.csv` | 6 × 34 |
| `PSI101_Pyrell_DustTrakA_PhaseCounts_2026-11-14_170034.csv` | 66 × 5 |
| `PSI101_Pyrell_DustTrakA_PhaseExceptions_2026-11-14_170034.csv` | 1,178 × 13 |
| `PSI101_Pyrell_DustTrakA_PhaseLineage_Differences_20261114_180826.csv` | 3,216 × 14 |
| `PSI101_Pyrell_DustTrakA_PhaseLineage_RunValidation_20261114_180826.csv` | 6 × 22 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_AnalogMeasurementComparison_20261114_183132.csv` | 98 × 17 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_AnalogMeasurementComparison_20261114_183955.csv` | 98 × 17 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_EpisodeControlMetrics_20261114_183132.csv` | 3,250 × 23 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_EpisodeControlMetrics_20261114_183955.csv` | 3,250 × 23 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_TimestampCycleIntervals_20261114_183132.csv` | 7,900 × 23 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_TimestampCycleIntervals_20261114_183955.csv` | 7,900 × 23 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_TransitionAlignedRows_20261114_183132.csv` | 373 × 61 |
| `PSI101_Pyrell_DustTrakA_PhaseReversal_TransitionAlignedRows_20261114_183955.csv` | 373 × 61 |
| `PSI101_Pyrell_DustTrakA_PhaseSummary_2026-11-14_170034.csv` | 12 × 16 |
| `PSI101_Pyrell_DustTrakA_Run87_FieldValues_2026-11-14_170034.csv` | 8 × 4 |
| `PSI101_Pyrell_DustTrakA_Run87_StageDiagnostics_2026-11-14_170034.csv` | 1 × 11 |
| `PSI101_Pyrell_DustTrak_Pair_Summary_2026-11-14.csv` | 14 × 12 |
| `PSI101_Pyrell_DustTrak_Paired_Samples_2026-11-14.csv` | 70 × 10 |
| `PSI101_Pyrell_DustTrak_Value_Clusters_2026-11-14.csv` | 43 × 9 |
| `PSI101_Pyrell_Experiment_Channel_Summary_2026-11-14.csv` | 70 × 12 |
| `PSI101_Pyrell_Instrument_State_Audit_2026-11-14.csv` | 151 × 12 |
| `PSI101_Pyrell_QA_2026-11-14.csv` | 7 × 14 |
| `PSI101_Pyrell_Raw_Channel_Range_Check_2026-11-14.csv` | 35 × 11 |
| `PSI101_Pyrell_Sentinel_Column_Audit_2026-11-14.csv` | 6 × 6 |

The five workspace text reports are `PSI101_Pyrell_DustTrakA_Periodicity_AuditReport_20261114_181648.txt`, `PSI101_Pyrell_DustTrakA_Periodicity_AuditReport_20261114_183947.txt`, `PSI101_Pyrell_DustTrakA_PhaseLineage_Reconciliation_20261114_180826.txt`, `PSI101_Pyrell_DustTrakA_PhaseReversal_CorrelationAuditReport_20261114_183132.txt`, and `PSI101_Pyrell_DustTrakA_PhaseReversal_CorrelationAuditReport_20261114_183955.txt`.

## 5. Structured condition matrix and external raw-data boundary

The 14-record `backend/data/catalogue/investigations.json` condition matrix exposes `o2_range_pct` (%), `pressure_range_psi` (psi), `airflow_range_cm_s` (cm/s), `hardware_rack`, `fuel_phase`, `gravity_regimes`, and `research_area`, with source URL, DOI status, and verification metadata. These are heterogeneous record-level envelopes. They are not a homogeneous per-test table and do not supply common ignition/extinction labels.

The repository contains no raw per-test tabular measurement files for BASS-II (PSI-25), SAFFIRE (PSI-98/99), FLEX (PSI-69/68), SPICE (PSI-107), SLICE (PSI-106), or ACME (PSI-20/22/159). Those investigations are catalogue metadata only here. No acquisition or web download was performed for this phase.

## 6. Six candidate prediction tasks

| Part 3 candidate | Phase 2 assessment | Evidence and scope |
|---|---|---|
| Combustion outcome classification | `NOT_TRAINABLE_FROM_LOCAL_RAW_DATA` | PSI-101 local files are smoke-aerosol instrument runs, not multi-material per-test ignition/combustion outcomes. |
| Flame extinction versus sustained combustion | `NOT_TRAINABLE_FROM_LOCAL_RAW_DATA` | BASS-II/FLEX conditions are catalogue-level envelopes; no local per-test extinction trial tables. |
| Ignition outcome classification | `NOT_TRAINABLE_FROM_LOCAL_RAW_DATA` | No local SAFFIRE or BRE per-sample ignition table. |
| Flame-spread or burning-rate regression | `NOT_TRAINABLE_FROM_LOCAL_RAW_DATA` | Simulator spread values are unvalidated surrogates, not measured labels. |
| Experimental condition similarity | `FEASIBLE_EXPLORATORY` | Descriptive similarity or regime profiling across 14 PSI envelopes and six run summaries; small-N only, no training in Phase 2. |
| Smoke or aerosol experimental classification, if suitable labelled data exists | `FEASIBLE_SUPERVISED_GROUPED_BY_RUN` **only for the narrow archived PSI-101 band/phase-exception subtask** | 7,886 non-mixed labeled cycles from six `RunID`s: 7,589 class 0 and 297 class 1. This is not fire detection, flame extinction, ignition, or smoke-versus-dust ground truth. Raw telemetry's seven runs have no independent aerosol/heating regime labels. |

The PSI-101 exception label is constructed from DustTrak-A measurement bands and the historical per-run phase mapping. For an exception target, exclude `ExpectedBand`, `ObservedBand`, `RelativeCyclePhase`, `ExceptionIndicator`, `MixedBandIndicator`, and duplicate-cycle fields from predictors. Cycle/time features may use only the current cycle index and past within-run time context. Raw rolling statistics, aerosol ratios, and temperature/resistance derivatives are computed from strictly earlier rows in the same run; `-999` remains missing.

`GroupedExperimentSplit` is deterministic, requires `RunID`, and asserts pairwise disjoint train/validation/test groups. The default six-run holdout assigns four runs to train, one to validation, and one to test; `GroupKFold` and Leave-One-Group-Out helpers support whole-run folds. Missing-value medians and scaling parameters are fit on training rows only. `UnitAwareStandardScaler` requires declared, matching feature units. This split design prevents adjacent rows/cycles from a single burn run being divided across partitions; it does not solve small-sample or label-validity limitations. No model was trained in Phase 2.

## 7. API and implementation inventory

New read-only endpoints are mounted in FastAPI and have `/api` aliases:

| Endpoint | Purpose |
|---|---|
| `GET /ml/datasets`, `GET /api/ml/datasets` | Full local registry, source/DOI/license provenance, file schemas, units, row/missingness/class statistics, run groups, and deployment availability. |
| `GET /ml/tasks`, `GET /api/ml/tasks` | The six exact candidate tasks with evidence-based status, target scope, group counts, class balance, limitations, and explicit `training_performed: false`. |
| `GET /ml/datasets/{dataset_id}/quality`, `GET /api/ml/datasets/{dataset_id}/quality` | Per-file/run counts and class distributions, missingness, and grouped-split overlap audit. Unknown dataset IDs return 404. |

The Phase 2 implementation is standard-library-only under `backend/ml/datasets/`, `backend/ml/preprocessing/`, and `backend/ml/features/`, with an APIRouter in `backend/ml/router.py`. It does not add a training model, external dataset fetcher, UI workspace, or dependency.

The installed local Ollama service was checked through `GET /api/ai/status` using FastAPI TestClient: HTTP 200, `online: true`, `available_models: ["qwen3:4b"]`, and `selected_model: "qwen3:4b"`. This verifies discovery only, not a live generation test.

## 8. Sources and reproducibility

- Local raw headers, row counts, intervals, sentinels: `data/raw/PSI-101/Pyrell/Run_*/HKPData_*.csv`; `data/metadata/PSI101_Pyrell_Column_Profile_2026-11-14.csv`; `data/metadata/PSI101_Pyrell_QA_2026-11-14.csv`; `data/metadata/PSI101_Pyrell_Sentinel_Column_Audit_2026-11-14.csv`.
- Run-87 eligibility: `data/metadata/PSI101_Pyrell_DustTrakA_Run87_StageDiagnostics_2026-11-14_170034.csv` and `data/metadata/PSI101_Pyrell_DustTrakA_Run87_FieldValues_2026-11-14_170034.csv`.
- Archive validation and six `RunID`s: `backend/app/archive.py`; `backend/data/metadata/`; `data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_AuditReport_20261114_183947.txt`.
- Catalogue fields: `backend/data/catalogue/investigations.json`; `backend/src/catalogue.py` (`REPOSITORY_SCOPE`); `docs/references.md`.
- DOI check: [DataCite PSI-101 record](https://api.datacite.org/dois/10.60555/2np7-jv14); [DataCite PSI-20 candidate record](https://api.datacite.org/dois/10.60555/vb93-3y72); [NASA PSI-101 record](https://psi.nasa.gov/physci/repo/data/investigations/PSI-101).
- Executable inspection: `backend/ml/datasets/registry.py`, `backend/ml/datasets/loader.py`, `backend/ml/preprocessing/pipeline.py`, `backend/ml/features/engineering.py`, `backend/ml/router.py`.
