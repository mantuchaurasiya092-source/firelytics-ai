# Two-minute judge demo

**Setup:** run `.\start-local.ps1`, or start the API and dashboard manually, then open `http://localhost:3000`.

**One-line opener:** “NASA PSI holds 24 combustion investigations and about 12.4 TB of data. FIRELYTICS turns 14 of them into a live fire-safety screening workbench, accounts for the other 10, and is explicit about what the data cannot yet prove.”

---

## 0:00–0:15 — Mission telemetry and repository scope

Point at the sticky telemetry bar:

- `14 VERIFIED NASA PSI INVESTIGATIONS · DOI-LINKED PROVENANCE`
- active habitat: `ISS USOS STANDARD CABIN · 21.0% O₂ · 14.7 PSI · 0.000g`
- five workspace tabs, including **All-in-One Executive View**.

Open **PSI Repository Coverage & Scope Matrix**. Show **24 investigations · ~12.4 TB**, the **14 deeply indexed** Tier 1 records and the **10 associated** Tier 2 studies. Close with the LUCI/FM2 line:

> “These are the upcoming lunar missions. We do not have their data. Our 0 g + 1 g + PSI-22 E-FIELD engine bounds the envelope they will test.”

---

## 0:15–0:45 — Artemis preset and the lunar dip

In **Mission & Habitat Simulator**, click **Artemis Lunar Base**.

The card loads **34% O₂ · 10.2 psi · 0.166 g** and immediately POSTs `/api/backend/simulate`. Show:

- O₂ partial pressure **3.47 psi**
- estimated MOC near **15.1%**
- buoyant velocity about **11.4 cm/s**
- E-FIELD equivalent **4.07 kV ≈ 1.6 kV/cm**

Then point at **Chart A** (O₂/pressure envelope): the BASS-II/SAFFIRE boundary, crimson flammable zone, emerald self-extinguishing zone, normoxic isobar and the five habitat markers. Click **EVA Spacesuit** to show the high-oxygen corner jump to **4.3 psi / 100% O₂**.

In **Chart B**, read the lunar annotation:

> “At 0.166 g the inflow is slow enough to feed oxygen but too weak for 1 g convective cooling or blowoff. The screening curve puts the hazard peak near the Moon, not at 0 g and not at 1 g.”

State the limit: “This is a hypothesis for experiment selection, not a measured lunar limit. LUCI and FM2 will test it.”

---

## 0:45–1:10 — Ranking and comparison

Scroll to **Ranked Studies**. Expand one investigation to show factor-level reasons, DOI and source links. Note that similarity and evidence coverage are separate, and neither is a safety score.

Switch to **Catalogue & Comparison Matrix**. Search `smoke`, filter rack `CIR` or `MSG`, then show the default four-way comparison:

`PSI-25 BASS-II` · `PSI-20 ACME-BRE` · `PSI-22 E-FIELD` · `PSI-69 FLEX`

The `/api/backend/compare` matrix shows hardware rack, fuel phase, O₂/pressure/airflow envelopes, sensors, predictive variables and DOI. The deltas panel calls out the **MSG/SPICE flow-duct lineage** versus the **CIR ACME/FLEX** lineage and warns that a shared rack does not mean interchangeable test conditions.

---

## 1:10–1:35 — SI fire-safety synthesis

Open **SI Fire-Safety Synthesis**. Walk the four columns:

1. **Prevention** — BASS-II/SAFFIRE material screening across the coupled O₂, pressure, ventilation and gravity envelope.
2. **Detection** — SAME/SAME-R pyrolysis smoke at **D₃₂ ≈ 0.1–0.5 µm** versus DAFT dust **> ~1 µm**, directly addressing nuisance alarms.
3. **Suppression** — FLEX CO₂/He inerting, MIST water mist and FLEX-2/CFI **500–800 K** cool-flame re-ignition.
4. **Earth spin-offs** — SCBA air tanks, PBI/Nomex turnout gear, dust-immune detectors and non-toxic water-mist extinguishers.

Mention the incident strip: Apollo 1, Apollo 13, Mir and the Artemis II smoke-alarm context.

---

## 1:35–2:10 — PSI-101 SAME-R lineage lab

Open **PSI-101 SAME-R Telemetry & Lineage Lab**.

- Select **Run 95** (or 84) and show classified cycles, phase exceptions and mixed-band exclusions.
- Show **Chart D**: phase/band agreement strip, exception positions and lag correlation.
- Enter a cycle number and inspect the returned **source-row and CSV-line references**.
- Say plainly: “Phase exceptions are classification mismatches, not fires, alarms or detector failures.”

---

## 2:10–2:25 — Export and close

Return to the simulator and click **Download CSV** and **Download HTML**. Open the HTML report:

- selected habitat parameters (O₂%, pressure psi, P₀₂ psi, gravity, buoyant velocity, MOC%, E-FIELD kV)
- ranked investigations with factor explanations and DOI links
- the full **14 core + 10 associated / ~12.4 TB** repository-scope note
- limitations

**Close:**

> “FIRELYTICS does not claim a habitat is safe. It shows which NASA experiments bound the answer, where the partial-gravity evidence stops, and exactly what LUCI and FM2 still need to measure.”
