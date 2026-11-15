"""NASA PSI catalogue, evidence matching, and transparent screening calculations.

These functions support research triage. They are not validated combustion
models, operational fire-safety assessments, or a source of new NASA data.
"""
from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOGUE_PATH = ROOT / "data" / "catalogue" / "investigations.json"
PSI_PER_ATM = 14.7
EARTH_PO2_PSI = 0.21 * PSI_PER_ATM
BUOYANT_SCALE_CMS_AT_1G = 28.0
ELECTRODE_GAP_CM = 2.54
MAX_EFIELD_KV = 10.0
GRAVITY_NODES: tuple[tuple[str, float], ...] = (
    ("0g", 0.0),
    ("0.05g", 0.05),
    ("lunar_0.166g", 0.166),
    ("mars_0.376g", 0.376),
    ("0.5g", 0.5),
    ("0.75g", 0.75),
    ("earth_1g", 1.0),
)

HABITAT_PROFILES: dict[str, dict[str, Any]] = {
    "iss_usos": {
        "id": "iss_usos",
        "name": "ISS USOS standard cabin",
        "o2_pct": 21.0,
        "pressure_psi": 14.7,
        "pressure_atm": 1.0,
        "po2_psi": round(0.21 * 14.7, 3),
        "airflow_range_cm_s": [5.0, 15.0],
        "gravity_g": 0.0,
        "gravity_regime": "Microgravity",
        "key_risk": "Normoxic partial pressure with continuous ventilation; smoke transport is forced-flow dominated.",
        "rationale": "Sea-level normoxic atmosphere used as the reference habitat for SAME-R, BASS-II and SAFFIRE comparisons.",
        "evidence_status": "Reference mission profile; verify against current program requirements before use.",
    },
    "artemis_lunar_base": {
        "id": "artemis_lunar_base",
        "name": "Lunar surface habitat screening profile",
        "o2_pct": 34.0,
        "pressure_psi": 10.2,
        "pressure_atm": round(10.2 / PSI_PER_ATM, 3),
        "po2_psi": round(0.34 * 10.2, 3),
        "airflow_range_cm_s": [8.0, 20.0],
        "gravity_g": 0.166,
        "gravity_regime": "Lunar partial gravity",
        "key_risk": "34% O₂ at 10.2 psi keeps partial pressure near sea level but raises oxygen mole fraction by roughly 60% relative to Earth air, narrowing ignition margins and reducing EVA pre-breathe time.",
        "rationale": "Low-pressure, oxygen-enriched atmosphere is a candidate for reducing structural mass and pre-breathe time; ACME BRE tested 10.2 psia / 26.5% O₂ and 8.2 psia / 34% O₂ ambients.",
        "evidence_status": "Scenario profile used for research screening; not an approved Artemis atmosphere specification.",
    },
    "mars_transit_habitat": {
        "id": "mars_transit_habitat",
        "name": "Mars transit / surface screening profile",
        "o2_pct": 26.5,
        "pressure_psi": 11.8,
        "pressure_atm": round(11.8 / PSI_PER_ATM, 3),
        "po2_psi": round(0.265 * 11.8, 3),
        "airflow_range_cm_s": [10.0, 10.0],
        "gravity_g": 0.376,
        "gravity_regime": "Mars partial gravity",
        "key_risk": "Oxygen-enriched low-pressure cabin with weak buoyancy; forced ventilation remains the dominant oxidizer-supply and smoke-transport mechanism.",
        "rationale": "Transit and surface habitat screening point bracketed by 0g test data, 1g screening and E-FIELD ion-convection evidence.",
        "evidence_status": "Scenario profile used for research screening; not a mission design specification.",
    },
    "eva_spacesuit": {
        "id": "eva_spacesuit",
        "name": "EVA suit screening profile",
        "o2_pct": 100.0,
        "pressure_psi": 4.3,
        "pressure_atm": round(4.3 / PSI_PER_ATM, 3),
        "po2_psi": round(1.0 * 4.3, 3),
        "airflow_range_cm_s": [15.0, 30.0],
        "gravity_g": 0.166,
        "gravity_regime": "Partial gravity",
        "key_risk": "Pure oxygen at 4.3 psi is above the sea-level oxygen partial pressure; any polymer ignition becomes an oxygen-fed fire in a confined, high-flow loop.",
        "rationale": "Illustrative suit-loop atmosphere used to show the oxygen-enrichment corner of the flammability envelope.",
        "evidence_status": "Illustrative suit-loop profile; not a validated suit fire-risk condition.",
    },
    "high_o2_testbed": {
        "id": "high_o2_testbed",
        "name": "Oxygen-enrichment research envelope",
        "o2_pct": 85.0,
        "pressure_psi": 14.7,
        "pressure_atm": 1.0,
        "po2_psi": round(0.85 * 14.7, 3),
        "airflow_range_cm_s": [5.0, 5.0],
        "gravity_g": 0.0,
        "gravity_regime": "Microgravity",
        "key_risk": "Extreme oxygen enrichment approaches the ACME CFI-G inverse-flame envelope; materials qualified for air are outside their validated range.",
        "rationale": "Upper oxygen-enrichment bound represented by CFI-G (PSI-159); research reference only.",
        "evidence_status": "Research-envelope reference only; not a habitable environment.",
    },
}


REPOSITORY_SCOPE: dict[str, Any] = {
    "title": "PSI Repository Coverage & Scope Matrix",
    "total_investigations": 24,
    "deeply_indexed_count": 14,
    "associated_count": 10,
    "aggregate_telemetry_tb": 12.4,
    "aggregate_telemetry_label": "~12.4 TB",
    "summary": (
        "NASA PSI contains 24 combustion-science investigations with roughly 12.4 TB of "
        "experimental telemetry, high-speed imaging and documents. FIRELYTICS deeply indexes "
        "the 14 spacecraft fire-safety and partial-gravity records in the catalogue and accounts "
        "for the remaining 10 associated studies as repository-completeness context."
    ),
    "id_reconciliation": (
        "Verified NASA PSI identifiers are used throughout. SAFFIRE-II/III is PSI-99 and SPICE is "
        "PSI-107; earlier brief placeholders PSI-135 and PSI-42 are corrected here to the "
        "DOI-verified catalogue records."
    ),
    "tier1": [
        {"psi_id": "PSI-101", "short_name": "SAME-R", "focus": "Pyrolysis smoke droplet sizing and DustTrak periodicity; archived cycle lineage analyzed locally.", "depth": "Deeply indexed · physics, DOI and local archived cycle lineage"},
        {"psi_id": "PSI-102", "short_name": "SAME", "focus": "Low-gravity smoke aerosol generation, transport and detector response.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-47", "short_name": "DAFT / DAFT-2", "focus": "Cabin and lunar dust aerosol standards; nuisance-alarm discrimination against smoke.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-26", "short_name": "BASS", "focus": "Burning and suppression of solid fuels in quiescent and forced-flow microgravity.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-25", "short_name": "BASS-II", "focus": "Forced-flow solid-fuel flammability and suppression envelopes.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-98", "short_name": "SAFFIRE-I", "focus": "Large-scale spacecraft fire growth and material flammability on Cygnus.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-99", "short_name": "SAFFIRE-II/III", "focus": "Large-scale fire growth, smoke transport and post-fire cleanup.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-20", "short_name": "ACME-BRE", "focus": "Quiescent elevated-oxygen burning and extinction limits in CIR.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-159", "short_name": "ACME-CFI-G", "focus": "Inverse and normal-gravity flame spread in oxygen-enriched atmospheres.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-22", "short_name": "ACME-E-FIELD", "focus": "Ion-driven body force as a 0g buoyancy analogue for partial-gravity bounding.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-69", "short_name": "FLEX", "focus": "Droplet combustion, inert-gas suppression and radiative extinction.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-68", "short_name": "FLEX-2/CFI", "focus": "Cool-flame vapor re-ignition and low-temperature droplet burning.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-107", "short_name": "SPICE", "focus": "Laminar smoke point and soot threshold in non-buoyant coflow flames.", "depth": "Deeply indexed · physics and DOI lineage"},
        {"psi_id": "PSI-106", "short_name": "SLICE", "focus": "Laminar coflow flame structure, liftoff and blowoff in microgravity.", "depth": "Deeply indexed · physics and DOI lineage"},
    ],
    "tier2": [
        {"key": "SOFIE", "name": "Solid Fuel Ignition and Extinction", "focus": "High-pressure / high-oxygen solid flammability chamber in CIR, complementing BASS-II and BRE.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "SAFFIRE-IV/V/VI", "name": "SAFFIRE IV / V / VI", "focus": "Large-scale spacecraft fire growth, smoke scrubbing and post-fire atmospheric cleanup on Cygnus.", "scope_status": "Associated PSI studies · repository-completeness context"},
        {"key": "ACME-CLD", "name": "ACME Coflow Laminar Diffusion Flame (CLD Flame)", "focus": "Soot and radiative structure in diluted coflow jets in CIR.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "ACME-s-Flame", "name": "ACME Structure & Response of Spherical Diffusion Flames (s-Flame)", "focus": "Radiative and convective extinction limits of spherical flames in CIR.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "FLEX-2J", "name": "FLEX-2J", "focus": "JAXA/NASA joint droplet combustion and flame spread along droplet arrays.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "FLEX-IT", "name": "FLEX-Italian (FLEX-IT)", "focus": "Slow convective droplet burning and radiative soot shells.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "FSDC", "name": "Fiber Supported Droplet Combustion", "focus": "Precursor shuttle/ISS droplet burning-rate constants.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "MIST", "name": "Water-Mist Fire Suppression Experiment", "focus": "Fine-water-mist interaction with microgravity flames; precursor to ISS Portable Fire Extinguisher and terrestrial spin-offs.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "LSP", "name": "Laminar Soot Processes", "focus": "Soot volume fraction and radiative heat loss in microgravity jet flames.", "scope_status": "Associated PSI study · repository-completeness context"},
        {"key": "CFE/ICF", "name": "CFE / ICF", "focus": "Capillary flow, interfacial combustion and porous-media polyurethane smoldering.", "scope_status": "Associated PSI studies · repository-completeness context"},
    ],
    "upcoming_missions": [
        {"key": "LUCI", "name": "Lunar-g Combustion Investigation", "status": "Upcoming NASA partial-gravity mission", "bounding": "Direct lunar-gravity flame-spread measurements will test the 0.166g screening dip. No LUCI data are claimed in this build."},
        {"key": "FM2", "name": "Flammability of Materials on the Moon", "status": "Upcoming NASA lunar material-flammability mission", "bounding": "Material-level lunar flammability limits will bound the 1g screening and 0g database used here. No FM2 data are claimed in this build."},
    ],
    "bounding_statement": (
        "LUCI (Lunar-g Combustion Investigation) and FM2 (Flammability of Materials on the Moon) are "
        "NASA's upcoming partial-gravity missions. Their safety envelopes are bounded here by the 0g "
        "database, 1g material screening and the PSI-22 ACME E-FIELD ion-driven buoyancy analogue; "
        "the application does not claim LUCI or FM2 measurements."
    ),
    "limitations": [
        "The ~12.4 TB aggregate is NASA PSI repository scope context, not a byte count of files downloaded or processed locally.",
        "Tier 2 records are catalogued for completeness and are not physics-indexed or used for ranking.",
        "Only the six selected PSI-101 Pyrell runs are locally analyzed; all other records remain catalogue evidence.",
        "The 24-investigation total is the PSI combustion-science scope; it is not a claim that all 24 are fire-safety experiments.",
    ],
}


def repository_scope() -> dict[str, Any]:
    """Return the 24-investigation / ~12.4 TB PSI repository scope accounting."""
    return REPOSITORY_SCOPE


def load_catalogue(path: Path | str | None = None) -> list[dict]:
    """Load the catalogue; an explicit path is accepted for verification tools."""
    source = Path(path) if path is not None else CATALOGUE_PATH
    return json.loads(source.read_text(encoding="utf-8"))


def habitat_profiles() -> list[dict[str, Any]]:
    """Return the validated research-screening atmosphere presets."""
    return list(HABITAT_PROFILES.values())


def _clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def _numeric_factor(study: dict, key: str, value: float | None, display_unit: str) -> tuple[str, str, float | None]:
    if value is None:
        return "Not compared", "No numeric scenario value supplied.", None
    if key == "airflow_range_cm_s" and study.get("airflow_max_cm_s") is not None:
        upper = float(study["airflow_max_cm_s"])
        if value <= upper:
            return "Within apparatus capability", f"NASA PSI states the apparatus could impose speeds up to {upper:g} cm/s; capability does not establish that this exact point was tested.", 0.5
        return "Outside documented capability", f"NASA PSI states apparatus speeds up to {upper:g} cm/s.", 0.0
    record = study.get(key)
    if key == "oxygen_comparison" and record is None:
        structured = study.get("o2_range_pct")
        if structured is None:
            return "Unknown", "The PSI overview does not state a comparable numeric condition.", None
        low, high = structured
        matched = low <= value <= high
        fact = f"Structured oxygen envelope is {low:g}–{high:g}% O₂ by volume."
        return ("Matches documented scope" if matched else "Outside documented scope", fact, 1.0 if matched else 0.0)
    if record is None:
        return "Unknown", "The PSI overview does not state a comparable numeric condition.", None
    if key == "oxygen_comparison":
        if record.get("operator") == "<":
            matched = value < float(record["value"])
            fact = f"Source states oxygen was varied below {record['value']} {record['unit']}; this is a study envelope, not a confirmed individual test point."
        else:
            return "Unknown", "No documented comparison rule for this condition.", None
    elif key == "pressure_range_atm":
        low, high = record
        matched = low <= value <= high
        fact = f"Recorded pressure range is {low:g}–{high:g} atm."
    elif key == "airflow_range_cm_s":
        low, high = record
        matched = low <= value <= high
        fact = study.get("airflow_recorded", f"Recorded airflow range is {low:g}–{high:g} cm/s.")
    else:
        return "Unknown", "No documented comparison rule for this condition.", None
    return ("Matches documented scope" if matched else "Outside documented scope", fact, 1.0 if matched else 0.0)


def _range_position(record: Any, value: float | None) -> float | None:
    """Normalized 0–1 position of a scenario value inside a documented range."""
    if value is None or not isinstance(record, (list, tuple)) or len(record) != 2:
        return None
    low, high = float(record[0]), float(record[1])
    if low <= value <= high:
        return 1.0
    span = max(high - low, 1.0)
    return max(0.0, 1.0 - min(abs(value - low), abs(value - high)) / (2.0 * span))


def _physics_proximity(study: dict, scenario: dict) -> dict[str, Any]:
    """Auxiliary continuous overlap metrics; never folded into the heuristic score."""
    oxygen = scenario.get("oxygen_pct")
    pressure_atm = scenario.get("pressure_atm")
    airflow = scenario.get("airflow_cm_s")
    flow_range = study.get("airflow_range_cm_s")
    if flow_range is None and study.get("airflow_max_cm_s") is not None:
        flow_range = [0.0, float(study["airflow_max_cm_s"])]
    components = {
        "oxygen_overlap": _range_position(study.get("o2_range_pct"), oxygen),
        "pressure_overlap": _range_position(study.get("pressure_range_psi"), pressure_atm * PSI_PER_ATM if pressure_atm is not None else None),
        "airflow_overlap": _range_position(flow_range, airflow),
    }
    known = [v for v in components.values() if v is not None]
    components["mean_overlap"] = round(sum(known) / len(known), 4) if known else None
    components["basis"] = "Continuous proximity only; documented match status and scores are unchanged."
    return components


def rank_studies(studies: list[dict], scenario: dict) -> list[dict]:
    """Rank documented evidence similarity; this is not a fire-risk score."""
    ranked = []
    for study in studies:
        factors = []
        def factor(name: str, status: str, explanation: str, score: float | None) -> None:
            factors.append({"factor": name, "status": status, "explanation": explanation, "score": score})
        wanted = scenario.get("pillar", "Any pillar")
        if wanted == "Any pillar":
            factor("Research pillar", "Not scored", "Scenario does not specify a desired pillar.", None)
        elif wanted in study["pillars"]:
            factor("Research pillar", "Matches", f"Catalogue classifies this study under {', '.join(study['pillars'])}.", 1.0)
        else:
            factor("Research pillar", "Does not match", f"Catalogue classifies this study under {', '.join(study['pillars'])}.", 0.0)
        material = scenario.get("material", "").strip().lower()
        source_material = study.get("fuel_or_sample", "")
        if not material:
            factor("Material / fuel", "Not compared", "No material or fuel supplied in the scenario.", None)
        elif "unknown" in source_material.lower() or "not specified" in source_material.lower():
            factor("Material / fuel", "Unknown", source_material, None)
        else:
            tokens = [t for t in material.replace("/", " ").replace("-", " ").split() if len(t) > 2]
            hits = [t for t in tokens if t in source_material.lower()]
            factor("Material / fuel", "Text match" if hits else "No text match", f"{'Scenario term(s) ' + ', '.join(hits) + ' appear in' if hits else 'Catalogue'} sample: {source_material}", 1.0 if hits else 0.0)
        factor("Oxygen concentration", *_numeric_factor(study, "oxygen_comparison", scenario.get("oxygen_pct"), "% O₂"))
        factor("Pressure", *_numeric_factor(study, "pressure_range_atm", scenario.get("pressure_atm"), "atm"))
        factor("Airflow", *_numeric_factor(study, "airflow_range_cm_s", scenario.get("airflow_cm_s"), "cm/s"))
        gravity = scenario.get("gravity", "Unknown")
        regimes = study.get("gravity_regimes", [])
        if gravity == "Microgravity" and ("Microgravity" in study.get("gravity_level", "") or "0g" in regimes):
            factor("Gravity regime", "Matches documented regime", study["gravity_level"], 1.0)
        elif gravity in ("Lunar partial gravity", "Mars partial gravity"):
            tag = "lunar_0.16g_mimic" if gravity.startswith("Lunar") else "mars_0.38g_mimic"
            if tag in regimes:
                factor("Gravity regime", "Proxy evidence available", "Electric-field ion-wind evidence is a body-force analogue that requires source-condition review before any gravity inference.", 0.5)
            else:
                factor("Gravity regime", "Evidence gap", "No direct lunar/Mars partial-gravity test is represented for this study.", None)
        elif gravity == "Unknown":
            factor("Gravity regime", "Not compared", "Scenario gravity regime is unspecified.", None)
        elif "Microgravity" in study.get("gravity_level", ""):
            factor("Gravity regime", "Different regime", study["gravity_level"], 0.0)
        else:
            factor("Gravity regime", "Unknown", study.get("gravity_level", "Not recorded"), None)
        scored = [f["score"] for f in factors if f["score"] is not None]
        applicable = [f for f in factors if f["status"] != "Not scored"]
        ranked.append({**study, "match_score": 100 * sum(scored) / len(scored) if scored else 0.0,
                       "evidence_coverage": 100 * len(scored) / len(applicable) if applicable else 0.0,
                       "matched_factor_count": sum(f["score"] in (0.5, 1.0) for f in factors),
                       "factor_count": len(scored), "ranking_factors": factors,
                       "physics_proximity": _physics_proximity(study, scenario)})
    return sorted(ranked, key=lambda x: (-x["match_score"], -x["evidence_coverage"], x["psi_id"]))


def rank_investigations(studies: list[dict], scenario: dict) -> list[dict]:
    """Backwards-compatible alias for the extended Phase-1 API."""
    return rank_studies(studies, scenario)


def _fuel_moc_reference(fuel_type: str) -> float:
    fuel = fuel_type.lower()
    if any(t in fuel for t in ("methanol", "heptane", "decane", "droplet")): return 14.0
    if any(t in fuel for t in ("pmma", "sibal", "cotton", "solid", "pyrell", "nomex", "silicone", "teflon", "kapton")): return 16.0
    if any(t in fuel for t in ("methane", "propane", "ethylene", "butane", "pentane", "gas")): return 12.0
    return 16.0


def _screening_point(g: float, airflow_cms: float, pressure_psi: float, reference_moc: float) -> dict[str, Any]:
    """Deterministic partial-gravity screening point (hypothesis, not measurement)."""
    buoyant = BUOYANT_SCALE_CMS_AT_1G * math.sqrt(max(g, 0.0))
    effective = math.hypot(airflow_cms, buoyant)
    # A shallow lunar-gravity hazard maximum is a visualization hypothesis, not data.
    lunar_enhancement = 1.1 * math.exp(-((g - 0.166) / 0.18) ** 2)
    cooling = max(0.0, effective - 25.0) * 0.035
    pressure_adjustment = (EARTH_PO2_PSI - (0.21 * pressure_psi)) * 0.20
    moc = _clamp(reference_moc - lunar_enhancement + cooling + pressure_adjustment, 5.0, 35.0)
    oxygen_supply = _clamp(effective / BUOYANT_SCALE_CMS_AT_1G, 0.0, 2.0)
    return {
        "gravity_g": round(g, 3),
        "moc_pct": round(moc, 2),
        "buoyant_flow_cms": round(buoyant, 2),
        "effective_velocity_cms": round(effective, 2),
        "oxygen_supply_index": round(oxygen_supply, 3),
        "cooling_penalty_pct": round(cooling, 3),
        "gravity_enhancement_pct": round(lunar_enhancement, 3),
    }


def compute_scientific_simulation(o2_pct: float, pressure_psi: float, airflow_cms: float, gravity_g: float, fuel_type: str = "generic material") -> dict[str, Any]:
    """Transparent partial-gravity visualization surrogate, never a safety model."""
    if not 0 <= o2_pct <= 100 or not 0 < pressure_psi <= 30 or not 0 <= airflow_cms <= 250 or not 0 <= gravity_g <= 2:
        raise ValueError("Scenario is outside the published screening input bounds.")
    reference_moc = _fuel_moc_reference(fuel_type)

    def point(g: float) -> dict[str, Any]:
        base = _screening_point(g, airflow_cms, pressure_psi, reference_moc)
        effective = base["effective_velocity_cms"]
        # Slow partial-gravity inflow feeds oxygen without the 1g convective cooling penalty.
        lunar_boost = 1.0 + 0.35 * math.exp(-((g - 0.166) / 0.2) ** 2)
        spread = max(0.0, (o2_percent - base["moc_pct"]) * 0.16 * lunar_boost / (1.0 + max(0.0, effective - 35.0) / 45.0))
        if effective < 3.0:
            regime = "Quiescent Diffusion-Limited"
        elif effective <= 25.0:
            regime = "Oxygen-Supply Enhanced (Peak Hazard Zone)"
        else:
            regime = "Convective Blowoff / Cooling Regime"
        return {**base, "flame_spread_rate_mms": round(spread, 3), "regime": regime}

    o2_percent = float(o2_pct)
    selected = point(gravity_g)
    po2 = o2_pct / 100 * pressure_psi
    regime = selected["regime"]
    flammability_index = _clamp(
        50.0
        + max(0.0, o2_pct - selected["moc_pct"]) * 2.0
        + (po2 / EARTH_PO2_PSI - 1.0) * 18.0
        - max(0.0, selected["effective_velocity_cms"] - 30.0) * 0.7,
        0.0,
        100.0,
    )
    gravity_curve = [point(g) for _, g in GRAVITY_NODES]
    peak = max(gravity_curve, key=lambda p: p["flame_spread_rate_mms"])

    def boundary_o2(psi: float) -> float:
        adjustment = (EARTH_PO2_PSI - 0.21 * psi) * 0.20
        return round(_clamp(selected["moc_pct"] + adjustment, 5.0, 35.0), 2)

    envelope = []
    boundary_curve = []
    for psi in (4.0, 7.0, 10.0, 14.7, 18.0):
        boundary = boundary_o2(psi)
        boundary_curve.append({"pressure_psi": psi, "boundary_o2_pct": boundary})
        for oxygen in (12.0, 15.0, 18.0, 21.0, 30.0, 34.0, 50.0, 75.0, 100.0):
            envelope.append({
                "pressure_psi": psi,
                "o2_pct": oxygen,
                "po2_psi": round(psi * oxygen / 100, 3),
                "boundary_o2_pct": boundary,
                "screening_side_of_boundary": "above_surrogate_moc" if oxygen >= boundary else "below_surrogate_moc",
            })
    markers = [{
        "id": profile["id"],
        "label": profile["name"],
        "o2_pct": profile["o2_pct"],
        "pressure_psi": profile["pressure_psi"],
        "gravity_g": profile["gravity_g"],
        "screening_side_of_boundary": "above_surrogate_moc" if profile["o2_pct"] >= boundary_o2(profile["pressure_psi"]) else "below_surrogate_moc",
    } for profile in HABITAT_PROFILES.values()]
    markers.append({"id": "user_scenario", "label": "User scenario", "o2_pct": o2_pct, "pressure_psi": pressure_psi,
                    "gravity_g": gravity_g,
                    "screening_side_of_boundary": "above_surrogate_moc" if o2_pct >= boundary_o2(pressure_psi) else "below_surrogate_moc"})
    voltage_kv = min(MAX_EFIELD_KV, MAX_EFIELD_KV * math.sqrt(max(gravity_g, 0.0)))
    field_kv_cm = voltage_kv / ELECTRODE_GAP_CM
    return {
        "model": {
            "name": "FIRELYTICS transparent partial-gravity screening surrogate",
            "version": "phase-1.1",
            "validated": False,
            "limitations": "MOC, spread, and flammability index are visualization surrogates, not NASA measurements, predictions, design limits, or safety determinations.",
            "evidence_basis": ["BASS-II (PSI-25) 0g forced-flow MOC data", "ACME BRE (PSI-20) quiescent elevated-O₂ burning", "ACME E-FIELD (PSI-22) ion-driven body force", "1g NASA material screening tests"],
        },
        "inputs": {"o2_pct": o2_pct, "pressure_psi": pressure_psi, "airflow_cms": airflow_cms, "gravity_g": gravity_g, "fuel_type": fuel_type},
        "metrics": {
            "po2_psi": round(po2, 3),
            "earth_sea_level_po2_psi": EARTH_PO2_PSI,
            "normoxic_equivalent_o2_pct_at_14_7_psi": round(po2 / PSI_PER_ATM * 100, 2),
            "buoyant_velocity_cms": selected["buoyant_flow_cms"],
            "effective_velocity_cms": selected["effective_velocity_cms"],
            "oxygen_supply_index": selected["oxygen_supply_index"],
            "estimated_moc_pct": selected["moc_pct"],
            "flammability_index": round(flammability_index, 1),
            "regime_classification": regime,
            "peak_hazard_gravity_g": peak["gravity_g"],
        },
        "gravity_curve": gravity_curve,
        "o2_pressure_envelope": envelope,
        "boundary_curve": boundary_curve,
        "habitat_markers": markers,
        "partial_gravity_bounding": {
            "bounding_anchors": [
                {"regime": "microgravity", "gravity_g": 0.0, "evidence": ["BASS (PSI-26)", "BASS-II (PSI-25)", "ACME BRE (PSI-20)", "ACME E-FIELD (PSI-22)"]},
                {"regime": "lunar", "gravity_g": 0.166, "evidence": ["ACME E-FIELD ion-wind analogue (PSI-22)", "LUCI / FM2 are planned targets; no local data"]},
                {"regime": "mars", "gravity_g": 0.376, "evidence": ["Interpolation between 0g and 1g bounds", "ACME E-FIELD ion-wind analogue (PSI-22)"]},
                {"regime": "earth", "gravity_g": 1.0, "evidence": ["NASA normal-gravity material screening (Test 1 / Test 2)"]},
            ],
            "hazard_peak": {"gravity_g": peak["gravity_g"], "moc_pct": peak["moc_pct"], "flame_spread_rate_mms": peak["flame_spread_rate_mms"]},
            "hypothesis": "At lunar gravity a slow buoyant inflow (about 11.4 cm/s) can replenish oxygen at the flame zone without the 1g convective cooling or blowoff that raises the apparent MOC, producing a local flammability maximum between quiescent 0g and 1g.",
            "status": "Visualization hypothesis; LUCI and FM2 are required to test it.",
        },
        "efield_equivalence": {
            "available": True,
            "method": "Illustrative experiment-selection scaling from the ACME E-FIELD 0–10 kV / 2.54 cm electrode configuration; no calibrated g-to-voltage conversion is asserted.",
            "target_gravity_g": gravity_g,
            "equivalent_voltage_kv": round(voltage_kv, 2),
            "electrode_gap_cm": ELECTRODE_GAP_CM,
            "estimated_equivalent_kv_cm": round(field_kv_cm, 2),
            "ion_velocity_match_cms": selected["buoyant_flow_cms"],
            "evidence_requirement": "Use E-FIELD test matrices and measured ion-current/flow data before claiming gravity equivalence.",
        },
    }


def _intersection(ranges: list[Any]) -> list[float] | None:
    valid = [r for r in ranges if isinstance(r, (list, tuple)) and len(r) == 2]
    if not valid:
        return None
    low = max(float(r[0]) for r in valid)
    high = min(float(r[1]) for r in valid)
    return [low, high] if low <= high else None


def synthesize_scientific_insights(studies: list[dict], scenario: dict, selected_ids: list[str] | None = None) -> dict[str, Any]:
    """Structured cross-investigation synthesis from catalogue metadata only."""
    chosen = [s for s in studies if not selected_ids or s["psi_id"] in selected_ids]
    if not chosen:
        return {"selected_ids": [], "commonalities": [], "deltas": [], "sections": {}, "insights": [], "limitations": ["No valid investigation IDs were selected."]}
    names = {s["short_name"] for s in chosen}
    ids = {s["psi_id"] for s in chosen}
    racks = sorted({s.get("hardware_rack", "Unspecified") for s in chosen})
    phases = sorted({s.get("fuel_phase", "Unspecified") for s in chosen})
    pillars = sorted({p for s in chosen for p in s.get("pillars", [])})
    variables = sorted({v for s in chosen for v in s.get("predictive_variables", [])})
    insights = []
    if {"SAME-R", "DAFT"} & names or {"PSI-101", "PSI-47"} & ids:
        insights.append({"domain": "Detection", "statement": "Separate pyrolysis smoke from nuisance dust using size and number-density signatures: SAME/SAME-R smoke droplets cluster near D32 ≈ 0.1–0.5 µm, whereas Arizona Road Dust and cabin particulate are dominated by particles above about 1 µm. DAFT's DustTrak/P-Trak comparison is the calibration precedent; the catalogue alone does not establish a deployment discriminator.", "evidence_status": "Catalogue synthesis plus PSI-101 archived DustTrak periodicity; no DAFT raw data processed locally."})
    if any(name.startswith("FLEX") for name in names) or {"PSI-69", "PSI-68"} & ids:
        insights.append({"domain": "Suppression", "statement": "FLEX provides inert-gas dilution limits (CO₂, He, SF₆) and radiative-extinction data; FLEX-2/CFI adds a 500–800 K cool-flame stage that can persist after the visible flame is out. Suppression verification must therefore include a post-extinguish re-ignition hold time, not only a visible-flame criterion.", "evidence_status": "Catalogue synthesis; not a suppressant recommendation."})
    if {"BASS", "BASS-II", "SAFFIRE-I", "SAFFIRE-II/III", "BRE", "E-FIELD"} & names:
        insights.append({"domain": "Prevention", "statement": "Screen materials across the coupled (O₂ mole fraction, total pressure, ventilation, gravity) envelope rather than against a single limiting-oxygen number. BRE shows that quiescent elevated-oxygen atmospheres can sustain burning where 21% O₂ self-extinguishes; BASS-II shows that increasing ventilation can revive a weak flame; SAFFIRE provides the large-scale growth bound.", "evidence_status": "Evidence-triage recommendation only."})
    if "E-FIELD" in names:
        insights.append({"domain": "Partial gravity", "statement": "E-FIELD ion-driven body forces can reproduce part of the buoyant inflow at 0g, bounding the lunar and Mars regimes between 0g data, 1g screening and the ion-wind analogue. It does not replace LUCI or FM2 direct measurements.", "evidence_status": "Hypothesis / experiment-selection guidance."})
    return {
        "selected_ids": [s["psi_id"] for s in chosen],
        "commonalities": [{
            "hardware_racks": racks,
            "fuel_phases": phases,
            "pillars": pillars,
            "shared_predictive_variables": variables,
            "o2_envelope_intersection_pct": _intersection([s.get("o2_range_pct") for s in chosen]),
            "pressure_envelope_intersection_psi": _intersection([s.get("pressure_range_psi") for s in chosen]),
            "airflow_envelope_intersection_cm_s": _intersection([s.get("airflow_range_cm_s") or [0.0, s.get("airflow_max_cm_s") or 0.0] for s in chosen]),
        }],
        "deltas": [{key: s.get(key) for key in ("psi_id", "short_name", "hardware_rack", "fuel_phase", "o2_range_pct", "pressure_range_psi", "airflow_range_cm_s", "airflow_max_cm_s", "gravity_regimes", "predictive_variables", "sensors_variables")} for s in chosen],
        "sections": {
            "prevention": [i["statement"] for i in insights if i["domain"] == "Prevention"],
            "detection": [i["statement"] for i in insights if i["domain"] == "Detection"],
            "suppression": [i["statement"] for i in insights if i["domain"] == "Suppression"],
            "partial_gravity": [i["statement"] for i in insights if i["domain"] == "Partial gravity"],
            "earth_spinoffs": [{"psi_id": s["psi_id"], **s["earth_spinoff"]} for s in chosen if isinstance(s.get("earth_spinoff"), dict)],
            "historical_incidents": sorted({incident for s in chosen for incident in s.get("historical_incident_links", [])}),
        },
        "insights": insights,
        "scenario": scenario,
        "limitations": [
            "Cross-investigation synthesis derives from catalogue metadata and does not merge raw experimental data.",
            "No output is a fire prediction, detector qualification, suppression recommendation, or operational safety assessment.",
            "Partial-gravity values are screening hypotheses bounded by 0g and 1g evidence plus the E-FIELD ion-wind analogue.",
        ],
    }
