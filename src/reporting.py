"""Deterministic, citation-carrying report exports."""
from __future__ import annotations

import csv
import html
import io

from .catalogue import REPOSITORY_SCOPE, HABITAT_PROFILES, compute_scientific_simulation

PSI_PER_ATM = 14.7
GRAVITY_G = {
    "Microgravity": 0.0,
    "Lunar partial gravity": 0.166,
    "Mars partial gravity": 0.376,
    "Earth gravity": 1.0,
    "Unknown": 0.0,
}
SCOPE_SUMMARY = (
    f"{REPOSITORY_SCOPE['total_investigations']} NASA PSI combustion investigations · "
    f"{REPOSITORY_SCOPE['aggregate_telemetry_label']} aggregate telemetry · "
    f"{REPOSITORY_SCOPE['deeply_indexed_count']} deeply indexed + "
    f"{REPOSITORY_SCOPE['associated_count']} associated"
)
SCOPE_COVERAGE = (
    "Core (14): " + "; ".join(f"{x['psi_id']} {x['short_name']}" for x in REPOSITORY_SCOPE["tier1"])
    + " | Associated (10): " + "; ".join(x["name"] for x in REPOSITORY_SCOPE["tier2"])
    + " | Upcoming: LUCI, FM2 (no mission data claimed)"
)


def _gravity_g(scenario: dict) -> float:
    value = scenario.get("gravity_g")
    if value is not None:
        return float(value)
    return float(GRAVITY_G.get(str(scenario.get("gravity", "Unknown")), 0.0))


def habitat_summary(scenario: dict) -> dict:
    """Selected-preset and derived screening parameters for report headers."""
    preset = HABITAT_PROFILES.get(str(scenario.get("habitat_id") or ""))
    oxygen = float(preset["o2_pct"]) if preset else scenario.get("oxygen_pct")
    pressure_atm = float(preset["pressure_atm"]) if preset else scenario.get("pressure_atm")
    pressure_psi = round(float(pressure_atm) * PSI_PER_ATM, 3) if pressure_atm is not None else None
    gravity = float(preset["gravity_g"]) if preset else _gravity_g(scenario)
    airflow = scenario.get("airflow_cm_s")
    if airflow is None and preset:
        low, high = preset["airflow_range_cm_s"]
        airflow = (float(low) + float(high)) / 2.0
    result = {
        "preset": preset["name"] if preset else "Custom scenario (no preset selected)",
        "habitat_id": preset["id"] if preset else "",
        "o2_pct": oxygen,
        "pressure_psi": pressure_psi,
        "po2_psi": round(float(oxygen) / 100.0 * pressure_psi, 3) if oxygen is not None and pressure_psi is not None else None,
        "gravity_g": gravity,
        "buoyant_velocity_cms": round(28.0 * (max(gravity, 0.0) ** 0.5), 2),
        "moc_pct": None,
        "efield_kv": None,
        "efield_kv_cm": None,
    }
    if oxygen is not None and pressure_psi is not None:
        try:
            simulation = compute_scientific_simulation(
                float(oxygen), float(pressure_psi), float(airflow or 0.0), gravity,
                str(scenario.get("material") or "generic material"),
            )
            result["moc_pct"] = simulation["metrics"]["estimated_moc_pct"]
            result["buoyant_velocity_cms"] = simulation["metrics"]["buoyant_velocity_cms"]
            result["efield_kv"] = simulation["efield_equivalence"]["equivalent_voltage_kv"]
            result["efield_kv_cm"] = simulation["efield_equivalence"]["estimated_equivalent_kv_cm"]
        except ValueError:
            pass
    return result


def ranking_csv(ranked: list[dict], scenario: dict | None = None, samer: dict | None = None) -> bytes:
    scenario=scenario or {}
    habitat=habitat_summary(scenario)
    runs={str(r['RunID']):r for r in (samer or {}).get('run_metrics',[])}
    processing_status=(samer or {}).get('processing_status','No SAME-R findings supplied.')
    rows=[]
    for i,x in enumerate(ranked):
        factors=x['ranking_factors']
        row={'Rank':i+1,'PSI_ID':x['psi_id'],'Name':x['name'],'DOI':x['doi'],
             'MatchScore':x['match_score'],'EvidenceCoverage':x['evidence_coverage'],
             'SourceURL':x['source_url'],'DOIURL':x['doi_url'],'License':x['license'],
             'LocalDataStatus':x['local_data_status'],
             'HabitatPreset':habitat['preset'],'HabitatID':habitat['habitat_id'],
             'Scenario':scenario.get('mission',''),'Gravity':scenario.get('gravity',''),
             'OxygenPct':scenario.get('oxygen_pct'),'PressureAtm':scenario.get('pressure_atm'),
             'PressurePsi':habitat['pressure_psi'],'PO2Psi':habitat['po2_psi'],
             'GravityG':habitat['gravity_g'],'BuoyantVelocityCmS':habitat['buoyant_velocity_cms'],
             'MOCPct':habitat['moc_pct'],'EFieldEquivalentKV':habitat['efield_kv'],
             'EFieldEquivalentKVcm':habitat['efield_kv_cm'],
             'AirflowCmS':scenario.get('airflow_cm_s'),'Material':scenario.get('material',''),
             'Pillar':scenario.get('pillar',''),
             'PSIRepositoryScope':SCOPE_SUMMARY,'PSIRepositoryCoverage':SCOPE_COVERAGE,
             'RankingExplanations':' | '.join(f"{f['factor']}: {f['status']} — {f['explanation']}" for f in factors),
             'UnknownOrUncompared':' | '.join(f"{f['factor']}: {f['status']}" for f in factors if f['score'] is None)}
        if runs:
            row['SAME-R processing status']=processing_status
            row['SAME-R findings']='; '.join(f"Run {rid}: {m.get('ClassifiedBinaryCycles')} classified cycles, {m.get('PhaseExceptions')} phase exceptions, {m.get('MixedBandCycles')} mixed-band excluded" for rid,m in sorted(runs.items()))
            row['SAME-R limitation']='Phase exceptions are classification mismatches, not fires, alarms, or confirmed detector failures.'
        rows.append(row)
    fields=list(rows[0]) if rows else ['Rank']
    stream=io.StringIO(newline='');writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader();writer.writerows(rows)
    return stream.getvalue().encode('utf-8-sig')


def _fmt(value: object, digits: int = 2) -> str:
    if value is None or value == "":
        return "unspecified"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def ranking_html(ranked: list[dict], scenario: dict, samer: dict | None = None) -> bytes:
    habitat=habitat_summary(scenario)
    body=[]
    for i,x in enumerate(ranked):
        factors=''.join(f"<tr><td>{html.escape(f['factor'])}</td><td>{html.escape(f['status'])}</td><td>{html.escape(f['explanation'])}</td></tr>" for f in x['ranking_factors'])
        body.append(f"<section><h2>{i+1}. {html.escape(x['short_name'])} ({html.escape(x['psi_id'])})</h2>"
                    f"<p>{html.escape(x['objective'])}</p><p>Similarity {x['match_score']:.1f}%; evidence coverage {x['evidence_coverage']:.1f}%.</p>"
                    f"<table><tr><th>Factor</th><th>Result</th><th>Explanation</th></tr>{factors}</table>"
                    f"<p>Sources: <a href='{html.escape(x['source_url'],quote=True)}'>NASA PSI record</a>; "
                    f"<a href='{html.escape(x['doi_url'],quote=True)}'>DOI {html.escape(x['doi'])}</a>. License: {html.escape(x['license'])}. "
                    f"Local data status: {html.escape(x['local_data_status'])}.</p></section>")
    runs=(samer or {}).get('run_metrics',[])
    same_table=''.join(f"<tr><td>{html.escape(str(r.get('RunID')))}</td><td>{html.escape(str(r.get('ClassifiedBinaryCycles')))}</td><td>{html.escape(str(r.get('PhaseExceptions')))}</td><td>{html.escape(str(r.get('MixedBandCycles')))}</td><td>{html.escape(str(r.get('MissingCycleNumbers')))}</td><td>{html.escape(str(r.get('DuplicateCycleNumbers')))}</td></tr>" for r in runs)
    status=html.escape((samer or {}).get('processing_status','No SAME-R findings supplied.'))
    same_section=(f"<h2>SAME-R archived findings</h2><p>{status} This is archive reconciliation, not independent scientific validation. Phase exceptions are classification mismatches, not fires, alarms, or confirmed detector failures. Original CSV measurement rows are not included.</p><table><tr><th>Run</th><th>Classified cycles</th><th>Phase exceptions</th><th>Mixed-band excluded</th><th>Missing cycle numbers</th><th>Duplicate cycles</th></tr>{same_table}</table>" if runs else '<h2>SAME-R</h2><p>No SAME-R run metrics were supplied for this export.</p>')
    habitat_section=(
        "<h2>Selected habitat parameters</h2>"
        f"<p><b>{html.escape(habitat['preset'])}</b>"
        + (f" · <code>{html.escape(habitat['habitat_id'])}</code>" if habitat['habitat_id'] else "")
        + "</p><table>"
        f"<tr><th>O₂ concentration</th><td>{_fmt(habitat['o2_pct'], 1)} %</td></tr>"
        f"<tr><th>Cabin pressure</th><td>{_fmt(habitat['pressure_psi'], 3)} psi ({_fmt((habitat['pressure_psi'] or 0) / PSI_PER_ATM if habitat['pressure_psi'] is not None else None, 3)} atm)</td></tr>"
        f"<tr><th>O₂ partial pressure</th><td>{_fmt(habitat['po2_psi'], 3)} psi</td></tr>"
        f"<tr><th>Gravity</th><td>{_fmt(habitat['gravity_g'], 3)} g</td></tr>"
        f"<tr><th>Buoyant velocity</th><td>{_fmt(habitat['buoyant_velocity_cms'], 2)} cm/s</td></tr>"
        f"<tr><th>Estimated MOC</th><td>{_fmt(habitat['moc_pct'], 2)} %</td></tr>"
        f"<tr><th>PSI-22 E-FIELD equivalent</th><td>{_fmt(habitat['efield_kv'], 2)} kV ≈ {_fmt(habitat['efield_kv_cm'], 2)} kV/cm</td></tr>"
        "</table><p>These are selected-preset or scenario-derived screening parameters, not measured flight values.</p>"
    )
    tier1=''.join(f"<li><b>{html.escape(x['psi_id'])}</b> — {html.escape(x['short_name'])}: {html.escape(x['focus'])}</li>" for x in REPOSITORY_SCOPE['tier1'])
    tier2=''.join(f"<li><b>{html.escape(x['name'])}</b> — {html.escape(x['focus'])}</li>" for x in REPOSITORY_SCOPE['tier2'])
    upcoming=''.join(f"<li><b>{html.escape(x['key'])}</b> — {html.escape(x['name'])}: {html.escape(x['bounding'])}</li>" for x in REPOSITORY_SCOPE['upcoming_missions'])
    scope_section=(
        "<h2>PSI repository coverage &amp; scope</h2>"
        f"<p><b>{SCOPE_SUMMARY}</b>. {html.escape(REPOSITORY_SCOPE['summary'])}</p>"
        f"<p>{html.escape(REPOSITORY_SCOPE['id_reconciliation'])}</p>"
        f"<h3>Tier 1 — 14 deeply indexed records</h3><ul>{tier1}</ul>"
        f"<h3>Tier 2 — 10 associated PSI studies</h3><ul>{tier2}</ul>"
        f"<h3>Upcoming partial-gravity missions</h3><ul>{upcoming}</ul>"
        f"<p>{html.escape(REPOSITORY_SCOPE['bounding_statement'])}</p>"
        f"<p class='note'>{html.escape(' '.join(REPOSITORY_SCOPE['limitations']))}</p>"
    )
    document=f"""<!doctype html><html lang="en"><meta charset="utf-8"><title>Firelytics AI evidence report</title>
<style>body{{font:16px Arial;max-width:1100px;margin:2rem auto;padding:0 1rem;color:#18313f}}table{{border-collapse:collapse;width:100%;margin:1rem 0}}td,th{{padding:.55rem;border:1px solid #ccd8df;text-align:left;vertical-align:top}}th{{background:#edf4f7}}section{{margin:2rem 0}}.limit{{background:#f1f5f6;padding:1rem}}.note{{font-size:12px;color:#365767}}</style>
<h1>Firelytics AI · Evidence report</h1>{habitat_section}<h2>Selected scenario</h2><p>{html.escape(str(scenario.get('mission','unspecified')))} / {html.escape(str(scenario.get('gravity','unspecified')))}; O₂ {html.escape(str(scenario.get('oxygen_pct') if scenario.get('oxygen_pct') is not None else 'unspecified'))}%; pressure {html.escape(str(scenario.get('pressure_atm') if scenario.get('pressure_atm') is not None else 'unspecified'))} atm; airflow {html.escape(str(scenario.get('airflow_cm_s') if scenario.get('airflow_cm_s') is not None else 'unspecified'))} cm/s; material {html.escape(str(scenario.get('material') or 'unspecified'))}; pillar {html.escape(str(scenario.get('pillar','unspecified')))}.</p>
<p>Scores rank documented research similarity, not safety. The weighted apparatus-capability comparison (0.5) is distinguished from observed experimental conditions. Unknown conditions remain unknown.</p><h2>Ranked investigations and factor explanations</h2>{''.join(body)}{same_section}{scope_section}
<div class="limit"><h2>Limitations</h2><p>Catalog-only investigations have not had raw experimental files processed by this application. Unknown conditions remain unknown. Partial-gravity results are not inferred. The report is not a validated fire prediction or operational safety assessment. NASA PSI record metadata is licensed CC0-1.0 as indicated on the source records; local raw-file redistribution terms are not established here.</p></div></html>"""
    return document.encode('utf-8')
