# Scientific methodology

FIRELYTICS AI is a deterministic, source-linked research-screening workbench. It does not train a fire model, invent measurements or issue safety verdicts. Every output is either NASA PSI metadata, a documented calculation, or an explicitly labelled screening surrogate.

## 1. Evidence base and repository scope

NASA PSI contains **24 combustion-science investigations** with roughly **12.4 TB** of experimental telemetry, high-speed imaging and documents.

- **Tier 1 — 14 deeply indexed records.** NASA PSI metadata, physics fields, DOI lineage and cross-investigation synthesis. Only PSI-101 has local archived cycle analysis.
  `PSI-101` SAME-R · `PSI-102` SAME · `PSI-47` DAFT · `PSI-26` BASS · `PSI-25` BASS-II · `PSI-98` SAFFIRE-I · `PSI-99` SAFFIRE-II/III · `PSI-20` ACME-BRE · `PSI-159` ACME-CFI-G · `PSI-22` ACME-E-FIELD · `PSI-69` FLEX · `PSI-68` FLEX-2/CFI · `PSI-107` SPICE · `PSI-106` SLICE
- **Tier 2 — 10 associated studies.** SOFIE, SAFFIRE-IV/V/VI, ACME CLD Flame, ACME s-Flame, FLEX-2J, FLEX-IT, FSDC, MIST, LSP and CFE/ICF. These are catalogued for repository completeness and are not used for ranking or physics.
- **Upcoming missions.** LUCI and FM2 are NASA's planned lunar-gravity investigations. Their envelopes are bounded by 0 g data, 1 g material screening and the PSI-22 E-FIELD analogue; no LUCI/FM2 measurements are claimed.

Verified identifiers are used: SAFFIRE-II/III is **PSI-99** and SPICE is **PSI-107**. Earlier brief placeholders `PSI-135` and `PSI-42` are corrected to the DOI-verified records.

The ~12.4 TB aggregate is repository-scope context, not a byte count of files downloaded or processed by this application.

## 2. Scenario ranking

Six dimensions are evaluated per study: research pillar, material/fuel, oxygen, pressure, airflow and gravity regime.

```text
match score = 100 × sum(known factor scores) / count(known factor scores)
evidence coverage = scored applicable factors / applicable factors
```

- A known match or in-scope condition scores 1.
- A known disagreement scores 0.
- A documented apparatus capability scores 0.5, because capability is not a tested condition.
- Unknown and unrequested factors are excluded from the denominator; they are never imputed.
- `physics_proximity` is reported separately and is **not** folded into the score.

The weights are equal and heuristic, not statistically calibrated. A similarity score is research relevance, never a probability of ignition or a safety rating.

## 3. Physics screening surrogate

The simulator takes O₂ mole fraction, total pressure, ventilation velocity, gravity and material, and returns a transparent seven-point gravity curve (0, 0.05, 0.166, 0.376, 0.5, 0.75 and 1 g).

For gravity `g`, the buoyant velocity scale is:

```text
V_buoyant = 28.0 × √g                    [cm/s]
V_effective = √(V_forced² + V_buoyant²)  [cm/s]
```

The screening MOC uses a fuel-family reference, a shallow lunar enhancement, a convective-cooling penalty and a pressure adjustment:

```text
MOC = MOC_reference
      − 1.10 × exp(−((g − 0.166) / 0.18)²)
      + max(0, V_effective − 25) × 0.035
      + (3.087 − 0.21 × P_psi) × 0.20
```

The lunar term is a **visualization hypothesis** that creates a local hazard maximum near **0.166 g**. It is not fitted to lunar measurements. The flame-spread surrogate and 0–100 flammability index are likewise screening aids, not predictions.

### Why the lunar dip matters

At 0.166 g, buoyant inflow is about **11.4 cm/s**. That is slow enough to replenish oxygen at the flame zone but too weak to produce the 1 g convective cooling or blowoff that raises the apparent MOC. The model therefore puts the peak flammability hazard between quiescent 0 g and 1 g, with an estimated MOC around **14.9–15.1%** depending on ventilation. LUCI and FM2 are required to test this.

### E-FIELD analogue

PSI-22 (ACME E-FIELD) used ion-driven body forces to control flames in microgravity. The workbench maps the selected gravity to an illustrative electrode voltage across the 2.54 cm gap:

```text
V_equiv = min(10 kV, 10 kV × √g)
E_equiv = V_equiv / 2.54 cm
```

For the lunar preset this gives **4.07 kV ≈ 1.6 kV/cm**. This is an experiment-selection scaling, not a calibrated gravity-to-voltage conversion. The application states that E-FIELD test matrices and ion-current data are required before any equivalence claim.

## 4. Habitat presets

| Preset | O₂ | Pressure | Gravity | Rationale |
|---|---:|---:|---:|---|
| ISS USOS cabin | 21% | 14.7 psi | 0 g | Normoxic reference with forced ventilation |
| Artemis lunar base | 34% | 10.2 psi | 0.166 g | Low-pressure, oxygen-enriched surface habitat |
| Mars transit / surface | 26.5% | 11.8 psi | 0.376 g | Weak buoyancy, ventilation-dominated transport |
| EVA spacesuit | 100% | 4.3 psi | 0.166 g | High-oxygen confined-loop corner |
| CFI-G testbed | 85% | 14.7 psi | 0 g | Oxygen-enrichment research envelope |

These are screening inputs, not approved operational atmosphere specifications.

## 5. Aerosol and nuisance-alarm discrimination

SAME/SAME-R Pyrell pyrolysis smoke is represented as liquid droplets near **D₃₂ ≈ 0.1–0.5 µm**. DAFT Arizona Road Dust and typical cabin particulate are dominated by particles **above about 1 µm**. The contrast is used to explain how size and number-density separation can reduce nuisance alarms while preserving smoke sensitivity.

This is a screening hypothesis. It is not a qualified detector algorithm, and no DAFT raw data are processed locally.

## 6. Suppression and cool flames

FLEX supplies inert-gas dilution and radiative-extinction evidence. FLEX-2/CFI supplies the low-temperature **500–800 K** cool-flame stage in which vapour can persist after visible extinction. MIST supplies the fine-water-mist lineage. The synthesis recommends verifying a post-extinguish hold time rather than declaring success when the visible flame disappears.

No suppressant quantity, agent concentration or design limit is asserted.

## 7. SAME-R archive reconciliation

The preserved root analysis replays the historical filters (`TestNumber = RunID`, `RunMode = 3`, `DustTrakAState = 6`, `DustTrakAPower = 1`), four measurement bands, per-run phase mapping, mixed-band rows and duplicates. It reconciles all six archived runs and exact exception-cycle identities.

The deployed backend serves the archived cycle ledger and source-row references, not the original CSV measurements, because local redistribution terms are not established. This is archive reconciliation, not independent scientific validation.

**Phase exceptions are classification mismatches, not fires, alarms or detector failures.**

## 8. Report exports

CSV and HTML reports include:

- selected habitat preset parameters: O₂%, pressure psi, P₀₂ psi, gravity g, buoyant velocity cm/s, simulated MOC% and PSI-22 E-FIELD equivalent kV/cm;
- ranked investigations with factor-level explanations and DOI links;
- the full 14 core + 10 associated PSI repository-scope note (~12.4 TB);
- SAME-R archived run summaries;
- limitations and source/licence notes.

## 9. What the model does not do

- It does not predict ignition, flame spread, detector response or time to untenable conditions.
- It does not interpolate partial-gravity behaviour as measured data.
- It does not merge raw data across investigations.
- It does not certify materials, atmospheres, detectors or suppression systems.
- It does not claim NASA endorsement or operational suitability.

The value is transparency: a judge, engineer or scientist can see which NASA experiments bound a scenario, which assumptions are surrogate, and where LUCI/FM2 must close the gap.
