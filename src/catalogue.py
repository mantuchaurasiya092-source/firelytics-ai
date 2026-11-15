"""Compatibility facade for the canonical backend catalogue/physics module.

The legacy Streamlit app and root tests retain their ``src.catalogue`` imports
while the implementation has one source of truth in ``backend/src/catalogue.py``.
"""
from backend.src.catalogue import (  # noqa: F401
    BUOYANT_SCALE_CMS_AT_1G,
    CATALOGUE_PATH,
    EARTH_PO2_PSI,
    ELECTRODE_GAP_CM,
    GRAVITY_NODES,
    HABITAT_PROFILES,
    MAX_EFIELD_KV,
    PSI_PER_ATM,
    REPOSITORY_SCOPE,
    compute_scientific_simulation,
    habitat_profiles,
    load_catalogue,
    rank_investigations,
    rank_studies,
    repository_scope,
    synthesize_scientific_insights,
)
