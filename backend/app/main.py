from __future__ import annotations

from typing import Literal
from functools import lru_cache

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from ai.router import router as ai_router
from app.archive import RUN_IDS, get_archive
from decision_support.router import router as decision_support_router
from digital_twin.router import router as digital_twin_router
from ml.router import router as ml_router
from telemetry.streaming import router as telemetry_router
from src.catalogue import (HABITAT_PROFILES, REPOSITORY_SCOPE,
                           compute_scientific_simulation, load_catalogue,
                           rank_studies, repository_scope,
                           synthesize_scientific_insights)
from src.reporting import ranking_csv, ranking_html

app=FastAPI(title='FIRELYTICS AI Research API',version='1.0.0',description=(
 'NASA PSI catalogue, evidence ranking, and reconciled archived SAME-R evidence. '
 'Deployment exposes archived analysis, not original-source replay.'
))
app.include_router(ai_router)
app.include_router(ml_router)
app.include_router(telemetry_router)
app.include_router(digital_twin_router)
app.include_router(decision_support_router)

@lru_cache(maxsize=1)
def _catalogue(): return load_catalogue()

class Scenario(BaseModel):
    model_config=ConfigDict(extra='forbid')
    mission: str=Field(min_length=1,max_length=120)
    gravity: Literal['Unknown','Microgravity','Lunar partial gravity','Mars partial gravity','Earth gravity']
    oxygen_pct: float|None=Field(default=None,ge=0,le=100)
    pressure_atm: float|None=Field(default=None,gt=0,le=20)
    airflow_cm_s: float|None=Field(default=None,ge=0,le=200)
    material: str=Field(default='',max_length=200)
    pillar: Literal['Any pillar','Prevention','Detection','Suppression']='Any pillar'
    gravity_g: float|None=Field(default=None,ge=0,le=2)
    habitat_id: str=Field(default='',max_length=80)

class SimulationScenario(BaseModel):
    """Validated input for the transparent research-screening visualization."""
    model_config=ConfigDict(extra='forbid')
    o2_pct: float=Field(ge=0,le=100)
    pressure_psi: float|None=Field(default=None,gt=0,le=30)
    pressure_atm: float|None=Field(default=None,gt=0,le=3)
    airflow_cms: float|None=Field(default=None,ge=0,le=250)
    airflow_cm_s: float|None=Field(default=None,ge=0,le=250)
    gravity_g: float=Field(ge=0,le=2)
    gravity_regime: str='Unknown'
    material: str=Field(default='',max_length=200)
    pillar: Literal['Any pillar','Prevention','Detection','Suppression']='Any pillar'
    mission: str=Field(default='Scientific screening scenario',min_length=1,max_length=120)
    habitat_id: str=Field(default='',max_length=80)

    def normalized(self) -> tuple[float,float,dict]:
        pressure=self.pressure_psi if self.pressure_psi is not None else (self.pressure_atm * 14.7 if self.pressure_atm is not None else None)
        if pressure is None:
            raise ValueError('Provide pressure_psi or pressure_atm.')
        flow=self.airflow_cms if self.airflow_cms is not None else (self.airflow_cm_s if self.airflow_cm_s is not None else 0.0)
        gravity_name=self.gravity_regime
        if gravity_name=='Unknown':
            gravity_name='Microgravity' if self.gravity_g == 0 else ('Lunar partial gravity' if abs(self.gravity_g-0.166)<0.03 else ('Mars partial gravity' if abs(self.gravity_g-0.376)<0.04 else 'Earth gravity'))
        scenario={'mission':self.mission,'gravity':gravity_name,'oxygen_pct':self.o2_pct,'pressure_atm':pressure/14.7,'airflow_cm_s':flow,'material':self.material,'pillar':self.pillar}
        return pressure,flow,scenario

class ComparisonRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    psi_ids: list[str]=Field(min_length=2,max_length=4)
    scenario: Scenario|None=None

def _run_id(run_id: str) -> str:
    if run_id not in RUN_IDS: raise HTTPException(404,detail=f'Run {run_id} is not in the validated PSI-101 Pyrell archive.')
    return run_id

@app.get('/health')
def health():
    archive=get_archive()
    return {'status':'ok','catalogue_records':len(_catalogue()),'samer_runs':len(archive['validation']),
            'archive_validation':'passed','raw_source_replay':'unavailable; raw source CSVs are not packaged'}

@app.get('/investigations')
def investigations():
    return {'items':_catalogue(),'repository_scope':REPOSITORY_SCOPE}

@app.get('/repository/scope')
@app.get('/api/repository/scope')
def get_repository_scope():
    """Account for all 24 NASA PSI combustion investigations and ~12.4 TB of scope."""
    return repository_scope()

@app.get('/investigations/{investigation_id}')
def investigation(investigation_id: str):
    found=next((x for x in _catalogue() if x['psi_id'].lower()==investigation_id.lower()),None)
    if found is None: raise HTTPException(404,detail=f'Investigation {investigation_id} was not found.')
    return found

@app.post('/scenarios/rank')
def scenario_rank(scenario: Scenario):
    ranked=rank_studies(_catalogue(),scenario.model_dump())
    return {'scenario':scenario.model_dump(),'score_interpretation':'Research evidence similarity only; not a safety rating or fire prediction.',
            'scoring_method':'100 * sum(known factor scores) / count(known factor scores); equal factor weights; apparatus capability contributes 0.5.',
            'items':ranked}

@app.get('/habitats')
@app.get('/api/habitats')
def habitats():
    """Return research-screening atmosphere profiles with their limitations."""
    return {'items':list(HABITAT_PROFILES.values()),
            'interpretation':'Profiles are research-screening inputs, not approved operational atmosphere requirements.'}

@app.post('/simulate')
@app.post('/api/simulate')
def simulate(scenario: SimulationScenario):
    try:
        pressure_psi,airflow_cms,ranking_scenario=scenario.normalized()
        simulation=compute_scientific_simulation(scenario.o2_pct,pressure_psi,airflow_cms,scenario.gravity_g,scenario.material)
    except ValueError as exc:
        raise HTTPException(422,detail=str(exc)) from exc
    studies=_catalogue()
    ranked=rank_studies(studies,ranking_scenario)
    selected=[item['psi_id'] for item in ranked[:4]]
    return {'scenario':{**ranking_scenario,'pressure_psi':pressure_psi,'airflow_cms':airflow_cms,'gravity_g':scenario.gravity_g},
            'simulation':simulation,'ranked_investigations':ranked,
            'synthesis':synthesize_scientific_insights(studies,ranking_scenario,selected),
            'repository_scope':REPOSITORY_SCOPE,
            'interpretation':'Physics output is a transparent visualization surrogate, not a validated prediction or safety assessment.'}

@app.post('/compare')
@app.post('/api/compare')
def compare(request: ComparisonRequest):
    requested=list(dict.fromkeys(request.psi_ids))
    if len(requested) != len(request.psi_ids):
        raise HTTPException(422,detail='psi_ids must not contain duplicates.')
    records={item['psi_id']:item for item in _catalogue()}
    missing=[psi_id for psi_id in requested if psi_id not in records]
    if missing:
        raise HTTPException(404,detail=f"Investigation IDs not found: {', '.join(missing)}")
    scenario=request.scenario.model_dump() if request.scenario else {'mission':'Comparison','gravity':'Unknown','oxygen_pct':None,'pressure_atm':None,'airflow_cm_s':None,'material':'','pillar':'Any pillar'}
    selected=[records[psi_id] for psi_id in requested]
    columns=['psi_id','short_name','objective','fuel_or_sample','hardware','hardware_rack','fuel_phase','oxygen_recorded','o2_range_pct','pressure_recorded','pressure_range_atm','pressure_range_psi','airflow_recorded','airflow_range_cm_s','gravity_level','gravity_regimes','sensors_variables','predictive_variables','earth_spinoff','historical_incident_links','source_url','doi','doi_url','license','local_data_status','verification_status']
    synthesis=synthesize_scientific_insights(selected,scenario,requested)
    return {'psi_ids':requested,'matrix':[{key:study.get(key) for key in columns} for study in selected],
            'deltas':synthesis.get('deltas',[]),'synthesis':synthesis,
            'interpretation':'Comparison preserves evidence status. Pending catalogue candidates require primary-source verification before scientific use.'}

@app.get('/samer/runs')
def samer_runs():
    archive=get_archive()
    return {'processing_status':archive['processing_status'],'runs':[{
      'run_id':rid,'first_cycle':int(archive['summaries'][rid]['FirstCycle']),
      'last_cycle':int(archive['summaries'][rid]['LastCycle']),
      'classified_cycles':int(archive['summaries'][rid]['ClassifiedCycles']),
      'phase_exceptions':int(archive['summaries'][rid]['ExceptionCycles']),
      'mixed_band_cycles':int(archive['summaries'][rid]['MixedBandCycles']),
      'duplicate_cycle_numbers':int(archive['summaries'][rid]['DuplicateCycleNumbers'])} for rid in RUN_IDS]}

@app.get('/samer/runs/{run_id}/validation')
def samer_validation(run_id: str):
    rid=_run_id(run_id);archive=get_archive()
    return {'run_id':rid,'status':'verified_archived_outputs','raw_replay_performed':False,
            'checks':next(x for x in archive['validation'] if x['run_id']==rid),
            'processing_status':archive['processing_status']}

@app.get('/samer/runs/{run_id}/summary')
def samer_summary(run_id: str):
    rid=_run_id(run_id);archive=get_archive();s=archive['summaries'][rid]
    return {'run_id':rid,'status':'verified_archived_outputs','raw_replay_performed':False,
            'processing_status':archive['processing_status'],'phase_summary':s,
            'periodicity_metrics':archive['metrics'][rid],
            'lag_correlations':[x for x in archive['lags'] if x.get('RunID')==rid],
            'candidate_models':[x for x in archive['models'] if x.get('RunID')==rid],
            'exception_cycles':sorted(archive['exceptions'][rid]),'mixed_cycle_ids':sorted(archive['mixed'][rid]),
            'block_events':[x for x in archive['blocks'] if x.get('RunID')==rid],
            'cycle_count':len(archive['cycles'][rid]),
            'source_data_note':'Cycle records retain original source row numbers and CSV line references. Raw measurement rows are not included in this deployment.'}

@app.get('/samer/runs/{run_id}/cycles/{cycle_id}')
def samer_cycle(run_id: str,cycle_id: int):
    rid=_run_id(run_id);archive=get_archive();cycle=archive['cycle_index'][rid].get(cycle_id)
    if cycle is None: raise HTTPException(404,detail=f'Cycle {cycle_id} is absent from the eligible archived sequence for Run {rid}; cycle gaps are preserved.')
    return {'run_id':rid,'cycle':cycle,'source_row_evidence':{
      'status':'references_only_raw_rows_not_packaged',
      'source_data_rows':cycle['SourceDataRowNumbers'],'csv_line_numbers':cycle['CSVLineNumbers'],
      'source_file':archive['source_files'][rid],
      'message':'These are exact source-row references from the validated cycle ledger. Original source row values are not included because the local source CSV redistribution terms are not established.'}}

def _report_payload(scenario: Scenario):
    archive=get_archive();ranked=rank_studies(_catalogue(),scenario.model_dump())
    samer={'run_metrics':[archive['metrics'][rid] for rid in RUN_IDS],
           'processing_status':archive['processing_status'],
           'raw_replay_performed':archive['raw_replay_performed']}
    return ranked,scenario.model_dump(),samer

@app.post('/reports/csv')
def report_csv(scenario: Scenario):
    ranked,sc,samer=_report_payload(scenario)
    return Response(ranking_csv(ranked,sc,samer),media_type='text/csv; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename="firelytics-scientific-report.csv"'})

@app.post('/reports/html')
def report_html(scenario: Scenario):
    ranked,sc,samer=_report_payload(scenario)
    return Response(ranking_html(ranked,sc,samer),media_type='text/html; charset=utf-8',
                    headers={'Content-Disposition':'attachment; filename="firelytics-scientific-report.html"'})

