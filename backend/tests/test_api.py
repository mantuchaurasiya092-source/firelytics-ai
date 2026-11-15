import csv
import io
import json
import sys
from pathlib import Path

import pytest

BACKEND=Path(__file__).resolve().parents[1]
ROOT=BACKEND.parent
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
if str(BACKEND) not in sys.path: sys.path.insert(0,str(BACKEND))

from fastapi.testclient import TestClient
from app.main import app

# Keep backend service imports from shadowing the preserved root modules when
# pytest collects both the legacy and API suites in one invocation.
sys.path.remove(str(BACKEND))
for name in tuple(sys.modules):
    if name=='src' or name.startswith('src.'):
        del sys.modules[name]

client=TestClient(app)

def test_phase_feature_routers_register_standard_and_api_aliases():
    registered={route.path for route in app.routes}
    expected={
      '/ai/status','/api/ai/status',
      '/ai/retrieve','/api/ai/retrieve',
      '/ai/chat','/api/ai/chat',
      '/ai/explain-simulation','/api/ai/explain-simulation',
      '/ai/generate-report','/api/ai/generate-report',
      '/ai/history','/api/ai/history',
      '/ml/datasets','/api/ml/datasets',
      '/ml/tasks','/api/ml/tasks',
      '/ml/datasets/{dataset_id}/quality','/api/ml/datasets/{dataset_id}/quality',
      '/ml/models','/api/ml/models',
      '/ml/predict','/api/ml/predict',
      '/ml/explainability/{model_id}','/api/ml/explainability/{model_id}',
      '/telemetry/mode','/api/telemetry/mode',
      '/telemetry/stream','/api/telemetry/stream',
      '/telemetry/upload','/api/telemetry/upload',
      '/digital-twin/simulate','/api/digital-twin/simulate',
      '/decision-support/synthesize','/api/decision-support/synthesize',
    }
    assert expected <= registered

def test_health_and_archived_validation_status():
    r=client.get('/health');assert r.status_code==200
    assert r.json()['archive_validation']=='passed'
    assert 'raw source CSVs are not packaged' in r.json()['raw_source_replay']

def test_investigation_endpoints():
    items=client.get('/investigations').json()['items']
    assert {'PSI-101','PSI-98','PSI-25','PSI-69','PSI-107','PSI-22','PSI-47','PSI-68'}.issubset({x['psi_id'] for x in items})
    assert len(items)==14
    assert client.get('/investigations/PSI-101').json()['doi']=='10.60555/2np7-jv14'
    assert client.get('/investigations/not-real').status_code==404

def test_habitat_simulation_and_comparison_endpoints():
    habitats=client.get('/habitats');assert habitats.status_code==200
    assert len(habitats.json()['items'])==5
    simulation=client.post('/simulate',json={'mission':'Lunar screening','o2_pct':34,'pressure_psi':10.2,'airflow_cms':12,'gravity_g':.166,'material':'Pyrell','pillar':'Prevention'})
    assert simulation.status_code==200
    body=simulation.json()
    assert body['simulation']['metrics']['po2_psi']==3.468
    assert len(body['simulation']['gravity_curve'])==7
    assert len(body['simulation']['boundary_curve'])==5
    assert body['simulation']['efield_equivalence']['equivalent_voltage_kv']>0
    assert body['simulation']['model']['validated'] is False
    assert body['synthesis']['sections']['prevention']
    assert body['synthesis']['sections']['earth_spinoffs']
    compare=client.post('/compare',json={'psi_ids':['PSI-101','PSI-47']})
    assert compare.status_code==200 and len(compare.json()['matrix'])==2
    assert compare.json()['matrix'][0]['hardware_rack']=='MSG'
    assert compare.json()['deltas'][0]['psi_id']=='PSI-101'

def test_rank_api_validates_and_reorders_real_catalogue():
    body={'mission':'ISS Pyrell detector','gravity':'Microgravity','oxygen_pct':None,'pressure_atm':None,
          'airflow_cm_s':None,'material':'Pyrell','pillar':'Detection'}
    first=client.post('/scenarios/rank',json=body);again=client.post('/scenarios/rank',json=body)
    assert first.status_code==200 and first.json()==again.json()
    assert first.json()['items'][0]['psi_id']=='PSI-101'
    assert 'not a safety rating' in first.json()['score_interpretation']
    lunar={**body,'mission':'Lunar suppression','gravity':'Lunar partial gravity','material':'methanol','pillar':'Suppression'}
    assert client.post('/scenarios/rank',json=lunar).json()['items'][0]['psi_id']=='PSI-69'
    assert client.post('/scenarios/rank',json={**body,'oxygen_pct':101}).status_code==422

def test_samer_runs_and_archived_validation_api():
    runs=client.get('/samer/runs').json()['runs']
    assert [x['run_id'] for x in runs]==['63','64','76','84','95','97']
    for run in runs:
        result=client.get(f"/samer/runs/{run['run_id']}/validation").json()
        assert result['status']=='verified_archived_outputs'
        assert result['raw_replay_performed'] is False
        assert all(v for k,v in result['checks'].items() if k!='run_id')
    assert client.get('/samer/runs/12/summary').status_code==404
    summary=client.get('/samer/runs/95/summary').json()
    assert len(summary['lag_correlations'])==40
    assert summary['candidate_models']
    assert all(x['RunID']=='95' for x in summary['candidate_models'])

def test_cycle_response_has_exact_original_row_references():
    r=client.get('/samer/runs/95/cycles/8677');assert r.status_code==200
    data=r.json();cycle=data['cycle'];evidence=data['source_row_evidence']
    refs=[int(x) for x in cycle['SourceDataRows'].split(';') if x]
    assert evidence['status']=='references_only_raw_rows_not_packaged'
    assert evidence['source_data_rows']==refs
    assert evidence['csv_line_numbers']==[x+1 for x in refs]
    assert evidence['source_file']=='Run_095/HKPData_gmt250_4.csv'
    assert client.get('/samer/runs/95/cycles/999999').status_code==404
    # Cross-check these references against the local raw file used by the preserved replay.
    from recover_phase_lineage import RAW,RUN_FILES
    with (RAW/RUN_FILES['95']).open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    for source_row in refs:
        original=rows[source_row-1]
        assert int(original['CycleCounter'])==8677

def test_report_downloads_are_valid_and_cited():
    scenario={'mission':'Lunar habitat','gravity':'Lunar partial gravity','oxygen_pct':None,
              'pressure_atm':None,'airflow_cm_s':None,'material':'Pyrell','pillar':'Detection'}
    r=client.post('/reports/csv',json=scenario);assert r.status_code==200
    assert 'text/csv' in r.headers['content-type'] and 'attachment;' in r.headers['content-disposition']
    rows=list(csv.DictReader(io.StringIO(r.text)))
    assert len(rows)==14 and rows[0]['Scenario']=='Lunar habitat'
    assert 'RankingExplanations' in rows[0] and 'Run 84:' in rows[0]['SAME-R findings']
    assert 'was not performed' in rows[0]['SAME-R processing status']
    h=client.post('/reports/html',json=scenario);assert h.status_code==200
    assert 'text/html' in h.headers['content-type'] and 'attachment;' in h.headers['content-disposition']
    assert len(h.content)>1000 and 'NASA PSI record' in h.text and '84</td>' in h.text
    assert 'was not performed in this deployment' in h.text

def test_ai_corpus_indexes_only_approved_records_archive_and_documents():
    from ai.rag.indexer import build_corpus

    chunks=build_corpus()
    catalogue_chunks=[item for item in chunks if item.source_type=='nasa_psi_catalogue_metadata']
    archive_chunks=[item for item in chunks if item.source_type=='verified_archived_summary']
    assert len({item.psi_id for item in catalogue_chunks})==14
    assert {f'Run {run}' for run in ('63','64','76','84','95','97')}.issubset({item.source_title.rsplit('· ',1)[-1] for item in archive_chunks})
    assert any(item.source_path_or_url=='docs/methodology.md' for item in chunks)
    assert any(item.psi_id=='PSI-101' and 'archive' in item.text.lower() for item in archive_chunks)
    assert all(not item.source_path_or_url.lower().endswith('.csv') for item in chunks)
    assert not any('data/raw/' in item.source_path_or_url.lower() for item in chunks)
    psi22={item.doi for item in catalogue_chunks if item.psi_id=='PSI-22'}
    assert psi22=={'psi_record_verified_doi_pending'}

def test_ai_retrieval_ranks_required_topics_with_provenance():
    from ai.rag.indexer import HybridIndex, build_corpus
    from ai.retrieval.retriever import Retriever

    retriever=Retriever(HybridIndex(build_corpus()))
    cases={
      'Lunar partial gravity E-FIELD':'PSI-22',
      'SAME-R Pyrell smoke vs DAFT dust':'PSI-101',
      'FLEX cool flames':'PSI-68',
    }
    for query,expected in cases.items():
        results=retriever.retrieve(query)
        assert results and expected in {item.chunk.psi_id for item in results}
        assert all(0.0<=item.relevance_score<=1.0 for item in results)
        assert all(item.citation()['source_path_or_url'] for item in results)
    same_dafts=retriever.retrieve('SAME-R Pyrell smoke vs DAFT dust')
    assert {'PSI-101','PSI-47'}.issubset({item.chunk.psi_id for item in same_dafts})
    assert retriever.retrieve('Lunar partial gravity E-FIELD')[0].chunk.psi_id=='PSI-22'
    assert retriever.retrieve('FLEX cool flames')[0].chunk.psi_id=='PSI-68'

def test_ai_offline_status_and_research_endpoints(monkeypatch):
    from urllib.error import URLError
    from ai.ollama.client import OllamaClient

    def offline(*_args,**_kwargs):
        raise URLError('Ollama is not running')

    monkeypatch.setattr('ai.ollama.client.urlopen',offline)
    monkeypatch.setenv('AI_ENABLE_OLLAMA_EMBEDDINGS','false')
    status=client.get('/api/ai/status')
    assert status.status_code==200
    status_body=status.json()
    assert status_body['online'] is False
    assert status_body['rag_index']['total_chunks']>0
    assert status_body['rag_index']['tier1_records_expected']==14
    assert any(item['name']=='qwen3:4b' and item['ram_requirement_gb']==3.5 for item in status_body['recommended_models'])
    assert any(item['name']=='qwen3:8b' and item['ram_requirement_gb']==6.0 for item in status_body['recommended_models'])
    assert client.get('/ai/status').status_code==200

    retrieval=client.post('/api/ai/retrieve',json={'query':'Lunar partial gravity E-FIELD','top_k':5})
    assert retrieval.status_code==200
    assert retrieval.json()['items'][0]['psi_id']=='PSI-22'
    assert retrieval.json()['items'][0]['doi']=='psi_record_verified_doi_pending'
    filtered=client.post('/api/ai/retrieve',json={'query':'Lunar partial gravity E-FIELD','psi_ids':['PSI-22'],'top_k':5})
    assert filtered.status_code==200 and all(item['psi_id']=='PSI-22' for item in filtered.json()['items'])

    chat=client.post('/api/ai/chat',json={
      'message':'Explain FLEX cool flames using NASA source context.',
      'task_type':'qa_with_citations',
      'session_id':'ai-offline-test',
    })
    assert chat.status_code==200
    chat_body=chat.json()
    assert chat_body['ollama_status']['generation_mode']=='offline_rag_deterministic'
    assert chat_body['epistemic_breakdown'].keys()=={
      'verified_nasa_findings','project_calculations','scientific_hypotheses','generated_suggestions'
    }
    assert chat_body['citations']

    simulation=client.post('/api/ai/explain-simulation',json={
      'simulation_inputs':{'gravity_g':0.166,'o2_pct':34.0,'pressure_psi':10.2},
      'simulation_outputs':{'metrics':{'po2_psi':3.468,'estimated_moc_pct':15.0}},
    })
    assert simulation.status_code==200 and simulation.json()['citations']

    report=client.post('/api/ai/generate-report',json={
      'scenario_context':{'mission':'Lunar partial-gravity screening'},
      'selected_psi_ids':['PSI-20','PSI-22'],
    })
    assert report.status_code==200 and report.json()['citations']
    assert '## Scope' in report.json()['answer_markdown']

    from app.main import _catalogue
    allowed_dois={item['doi'] for item in _catalogue() if item.get('doi','').startswith('10.')}
    for response in (chat.json(),simulation.json(),report.json()):
        assert response['safety_disclaimer']
        for citation in response['citations']:
            doi=citation['doi']
            assert doi is None or doi=='psi_record_verified_doi_pending' or doi in allowed_dois
    history=client.get('/api/ai/history',params={'session_id':'ai-offline-test'}).json()
    assert len(history['messages'])==2
    assert client.delete('/api/ai/history',params={'session_id':'ai-offline-test'}).json()['cleared'] is True

def test_ai_local_generation_rejects_unretrieved_citations_dois_and_values(monkeypatch):
    from ai.ollama.client import OllamaClient

    def online_status(self):
        return {
          'online':True,'base_url':self.base_url,'available_models':['qwen3:4b'],
          'selected_model':'qwen3:4b','recommended_models':[],'total_memory_gb':None,
          'status_message':'Local test model is online.',
        }

    def hallucinated_response(self,_model,_messages):
        return 'NASA observed 98765.4321 psi [PSI-999], valid DOI 10.60555/byp8-h018, and DOI 10.9999/fabricated.',7

    monkeypatch.setattr(OllamaClient,'status',online_status)
    monkeypatch.setattr(OllamaClient,'chat',hallucinated_response)
    response=client.post('/api/ai/chat',json={
      'message':'Explain FLEX cool flames using NASA source context.',
      'task_type':'qa_with_citations',
    })
    assert response.status_code==200
    body=response.json()
    assert body['ollama_status']['generation_mode']=='local_ollama_rag'
    assert 'PSI-999' not in body['answer_markdown']
    assert '10.9999/fabricated' not in body['answer_markdown']
    assert '10.60555/byp8-h018' in body['answer_markdown']
    assert '98765.4321' not in body['answer_markdown']
    assert '[unsupported citation removed]' in body['answer_markdown']
    assert '[unverified DOI removed]' in body['answer_markdown']
    assert '[unverified value removed]' in body['answer_markdown']

def test_ml_dataset_registry_matches_local_data_and_provenance():
    response=client.get('/api/ml/datasets')
    assert response.status_code==200
    body=response.json()
    assert body['dataset_counts']['tier1_catalogue_records']==14
    assert body['dataset_counts']['tier2_scope_records']==10
    assert body['dataset_counts']['local_raw_run_csvs']==7
    assert body['dataset_counts']['local_raw_run_rows']==10350
    assert body['dataset_counts']['archived_cycle_records']==7900

    datasets={item['dataset_id']:item for item in body['datasets']}
    catalogue=datasets['psi_catalogue_tier1_conditions']
    assert catalogue['record_count']==14
    psi101=next(record for record in catalogue['records'] if record['psi_id']=='PSI-101')
    assert psi101['doi']=='10.60555/2np7-jv14'
    assert psi101['provenance']['doi_status']=='verified_in_datacite_at_check_date'
    psi20=next(record for record in catalogue['records'] if record['psi_id']=='PSI-20')
    assert psi20['provenance']['doi_status']=='datacite_returned_404_at_check_date'
    psi22=next(record for record in catalogue['records'] if record['psi_id']=='PSI-22')
    assert psi22['provenance']['doi_status']=='pending_in_catalogue'
    raw=datasets['psi101_raw_telemetry']
    source_rows=0
    for path in (ROOT/'data'/'raw'/'PSI-101'/'Pyrell').glob('Run_*'+'/*.csv'):
        with path.open(encoding='utf-8-sig',newline='') as handle:
            source_rows+=sum(1 for _ in csv.DictReader(handle))
    assert raw['record_count']==source_rows==10350
    assert raw['deployment_availability']=='local_raw_only'
    assert {file['dataset_id'].rsplit('_',1)[-1] for file in raw['files']}=={'63','64','76','84','87','95','97'}
    raw_schema={column['name']:column['unit'] for column in raw['schema']}
    assert raw_schema['DustTrakAMeasurement(MgPerM3)']=='mg/m³'
    assert raw_schema['DustTrakAAnalogMeasurement(Volts)']=='V'
    assert raw_schema['PTrakMeasurement(PtPerCC)']=='particles/cm³'
    cycle=datasets['psi101_archived_cycle_sequence']
    assert cycle['deployment_availability']=='bundled_in_production'
    assert cycle['record_count']==7900
    assert cycle['provenance']['doi']=='10.60555/2np7-jv14'
    assert all(item['raw_tabular_files_local']==0 for item in body['unavailable_external_raw'])
    assert len(client.get('/ml/datasets').json()['datasets'])==len(body['datasets'])

def test_ml_task_feasibility_and_archived_group_quality_audit():
    response=client.get('/api/ml/tasks')
    assert response.status_code==200
    tasks=response.json()['tasks']
    assert len(tasks)==6
    by_id={task['task_id']:task for task in tasks}
    for task_id in (
        'task_1_combustion_outcome',
        'task_2_extinction_sustained',
        'task_3_ignition_outcome',
        'task_4_flame_spread_regression',
    ):
        assert by_id[task_id]['status']=='NOT_TRAINABLE_FROM_LOCAL_RAW_DATA'
        assert by_id[task_id]['trainable_from_local_data'] is False
    assert by_id['task_5_condition_similarity']['status']=='FEASIBLE_EXPLORATORY'
    task6=by_id['task_6_psi101_archived_band_exception']
    assert task6['status']=='FEASIBLE_SUPERVISED_GROUPED_BY_RUN'
    assert task6['record_count']==7886
    assert task6['group_count']==6
    assert isinstance(task6['training_performed'],bool)
    assert 'not fire' in task6['target_definition']
    assert all(item['raw_tabular_files_local']==0 for item in client.get('/api/ml/datasets').json()['unavailable_external_raw'])

    quality=client.get('/api/ml/datasets/psi101_archived_cycle_sequence/quality')
    assert quality.status_code==200
    body=quality.json()
    assert body['record_count']==7900
    assert body['grouping']['group_column']=='RunID'
    assert body['grouping']['group_ids']==['63','64','76','84','95','97']
    assert body['class_distribution']=={'0':7589,'1':297}
    audit=body['grouped_split_audit']
    assert audit['leakage_check_passed'] is True
    partitions=audit['partitions']
    train=set(partitions['train']['run_ids'])
    validation=set(partitions['validation']['run_ids'])
    test=set(partitions['test']['run_ids'])
    assert train.isdisjoint(validation)
    assert train.isdisjoint(test)
    assert validation.isdisjoint(test)
    assert set(body['leakage_excluded_fields']).issuperset({
        'ExpectedBand','ObservedBand','RelativeCyclePhase','ExceptionIndicator','MixedBandIndicator'
    })
    assert client.get('/api/ml/datasets/not_a_dataset/quality').status_code==404

def test_grouped_split_and_preprocessing_are_run_safe_and_train_fitted():
    from ml.preprocessing.pipeline import (
        GroupedExperimentSplit,
        UnitAwareStandardScaler,
        apply_median_imputer,
        fit_median_imputer,
    )

    rows=[
        {'RunID':str(run),'signal':float(run),'missing':'-999','label':str(run%2)}
        for run in range(6)
        for _ in range(3)
    ]
    split=GroupedExperimentSplit(random_state=7).split(
        rows,target_col='label',feature_columns=['signal','missing']
    )
    train_runs={row['RunID'] for row in split.train}
    validation_runs={row['RunID'] for row in split.validation}
    test_runs={row['RunID'] for row in split.test}
    assert train_runs.isdisjoint(validation_runs)
    assert train_runs.isdisjoint(test_runs)
    assert validation_runs.isdisjoint(test_runs)
    assert split.report['leakage_check_passed'] is True
    folds=GroupedExperimentSplit().leave_one_group_out(rows,target_col='label')
    assert len(folds)==6
    assert all(fold['report']['leakage_check_passed'] for fold in folds)

    medians=fit_median_imputer(split.train,['missing'])
    assert medians['missing'] is None
    usable_train=[{'x':1.0,'run':'train'},{'x':3.0,'run':'train'}]
    scaler=UnitAwareStandardScaler().fit(usable_train,{'x':'mg/m³'})
    transformed=scaler.transform([{'x':2.0}],{'x':'mg/m³'})
    assert transformed[0]['x']==0.0
    with pytest.raises(ValueError,match='units differ'):
        scaler.transform([{'x':2.0}],{'x':'particles/cm³'})

def test_scientific_features_are_causal_and_exclude_archive_labels():
    from ml.features.engineering import engineer_cycle_features, engineer_telemetry_features

    channel='DustTrakAMeasurement(MgPerM3)'
    raw=[
        {'RunID':'63','ElapsedTestTime(Secs)':'10',channel:'10000',
         'DustTrakBMeasurement(MgPerM3)':'10','PTrakMeasurement(PtPerCC)':'1000'},
        {'RunID':'63','ElapsedTestTime(Secs)':'11',channel:'20000',
         'DustTrakBMeasurement(MgPerM3)':'20','PTrakMeasurement(PtPerCC)':'2000'},
    ]
    engineered=engineer_telemetry_features(raw)
    first,second=engineered['rows']
    assert first['past_dusttrakameasurement_mgperm3_mean'] is None
    assert second['past_dusttrakameasurement_mgperm3_mean']==10000.0
    assert second['past_dusttrak_a_to_b_mass_ratio']==1000.0
    assert second['past_ptrak_to_dusttrak_a']==0.1
    changed_current=[dict(raw[0]),{**raw[1],channel:'99999'}]
    changed=engineer_telemetry_features(changed_current)['rows'][1]
    assert changed['past_dusttrakameasurement_mgperm3_mean']==second['past_dusttrakameasurement_mgperm3_mean']

    cycles=[
        {'RunID':'63','Cycle':'10','FirstTimestampSeconds':'100',
         'ExpectedBand':'A','ObservedBand':'B','ExceptionIndicator':'1',
         'MixedBandIndicator':'0','RelativeCyclePhase':'Phase0'},
        {'RunID':'63','Cycle':'12','FirstTimestampSeconds':'104',
         'ExpectedBand':'B','ObservedBand':'B','ExceptionIndicator':'0',
         'MixedBandIndicator':'0','RelativeCyclePhase':'Phase1'},
    ]
    cycle_features=engineer_cycle_features(cycles)['rows']
    assert cycle_features[1]['cycle_gap_from_previous']==2.0
    assert not any(key in cycle_features[1] for key in ('ExceptionIndicator','ExpectedBand','ObservedBand','RelativeCyclePhase'))

def test_ai_status_reports_local_qwen_model_from_ollama(monkeypatch):
    from ai.ollama.client import OllamaClient

    monkeypatch.setattr(OllamaClient,'list_models',lambda self:['qwen3:4b'])
    response=client.get('/api/ai/status')
    assert response.status_code==200
    body=response.json()
    assert body['online'] is True
    assert 'qwen3:4b' in body['available_models']
    assert body['selected_model']=='qwen3:4b'

def test_binary_metrics_and_exact_interventional_shapley():
    from ml.evaluation.metrics import classification_metrics
    from ml.explainability.explainer import exact_interventional_shap_summary

    metrics=classification_metrics([0,0,1,1],[0.1,0.8,0.2,0.9])
    assert metrics['accuracy']==0.5
    assert metrics['roc_auc']==0.75
    assert metrics['confusion_matrix']['matrix']==[[1,1],[1,1]]
    assert metrics['calibration']['status']=='diagnostic_only_not_calibration_adjusted'
    assert metrics['calibration']['brier_score']==0.325

    rows=[[0.0,0.0],[1.0,0.0],[0.0,1.0],[1.0,1.0]]
    def prediction(samples):
        return [0.2+0.1*row[0]+0.2*row[1] for row in samples]
    explanation=exact_interventional_shap_summary(
        prediction,rows,['x','y'],{'x':'mg/m³','y':'°C'},background_size=4,explained_size=4
    )
    summary={item['feature']:item for item in explanation['summary']}
    assert summary['x']['mean_abs_shap']==0.05
    assert summary['y']['mean_abs_shap']==0.1
    assert explanation['feature_count']==2

def test_training_rows_use_independent_channels_and_preserve_run_groups():
    from ml.training.trainer import FEATURE_NAMES, build_training_dataset

    rows=build_training_dataset()
    assert len(rows)==7886
    assert {row['RunID'] for row in rows}=={'63','64','76','84','95','97'}
    assert {row['target'] for row in rows}=={0,1}
    assert sum(row['target']==0 for row in rows)==3946
    assert sum(row['target']==1 for row in rows)==3940
    assert all(not name.lower().startswith('dusttraka') for name in FEATURE_NAMES)
    assert all('ObservedBand' not in row and 'ExceptionIndicator' not in row for row in rows)

def test_ml_registry_reports_missing_local_artifacts_without_fallbacks(tmp_path, monkeypatch):
    import ml.models.runtime as runtime

    monkeypatch.setattr(runtime, "REGISTRY_PATH", tmp_path / "registry.json")
    runtime.load_model_registry.cache_clear()
    try:
        response = client.get("/api/ml/models")
        assert response.status_code == 503
        detail = response.json()["detail"]
        assert "backend/ml/models/artifacts/registry.json" in detail
        assert "git-ignored pending PSI-101 file-rights review" in detail
        assert "not generated automatically by the API" in detail
    finally:
        runtime.load_model_registry.cache_clear()


def test_ml_model_registry_prediction_and_explainability_routes_with_safe_fixture(tmp_path,monkeypatch):
    import ml.models.runtime as runtime

    artifact={
        'artifact_format':'firelytics-safe-json-v1',
        'model_id':'fixture_model',
        'model_version':'0.0.1',
        'dataset_id':'fixture_dataset',
        'target_name':'ObservedBand',
        'target_interpretation':'Test fixture only; no scientific result.',
        'class_names':{'0':'10000-14999','1':'20000+'},
        'decision_threshold':0.5,
        'feature_names':['sensor_value'],
        'feature_schema':[{'name':'sensor_value','label':'Fixture sensor','unit':'mg/m³'}],
        'preprocessing':{'imputation_medians':[0.0],'standard_scaler':None},
        'estimator':{'kind':'logistic_regression','coefficients':[2.0],'intercept':0.0},
        'grouped_evaluation':{'method':'fixture grouped split','leakage_check_passed':True},
        'safety_disclaimer':'Test-only fixture; not a fire prediction or operational recommendation.',
        'explainability':{
            'method':'Test fixture only.',
            'data_scope':'Synthetic API fixture; not a trained scientific model.',
            'global_feature_importance':[{'feature':'sensor_value','importance':1.0}],
            'shap_summary':[{'feature':'sensor_value','mean_abs_shap':0.2}],
        },
    }
    summary={
        'model_id':'fixture_model',
        'version':'0.0.1',
        'display_name':'API contract fixture',
        'algorithm':'test-only logistic fixture',
        'artifact_path':'fixture_model.json',
        'validation_metrics':{
            'accuracy':0.5,'precision':0.5,'recall':0.5,'f1':0.5,'roc_auc':0.5,
            'confusion_matrix':{'labels':['0','1'],'matrix':[[1,1],[1,1]]},
            'roc_curve':[{'false_positive_rate':0.0,'true_positive_rate':0.0}],
        },
        'feature_importance':artifact['explainability']['global_feature_importance'],
        'safety_disclaimer':'Test-only fixture; not a fire prediction or operational recommendation.',
    }
    artifact_root=tmp_path/'artifacts'
    artifact_root.mkdir()
    (artifact_root/'fixture_model.json').write_text(json.dumps(artifact),encoding='utf-8')
    (artifact_root/'registry.json').write_text(json.dumps({
        'task_id':'fixture_task',
        'task_name':'Test fixture',
        'target_interpretation':artifact['target_interpretation'],
        'training_performed':True,
        'record_count':4,
        'run_ids':['A','B','C'],
        'grouped_evaluation_method':'fixture grouped split',
        'runid_leakage_check_passed':True,
        'model_artifacts_local_only':True,
        'safety_disclaimer':'Test-only fixture; not a fire prediction or operational recommendation.',
        'models':[summary],
    }),encoding='utf-8')
    monkeypatch.setattr(runtime,'ARTIFACT_ROOT',artifact_root)
    monkeypatch.setattr(runtime,'REGISTRY_PATH',artifact_root/'registry.json')
    runtime.load_model_registry.cache_clear()
    runtime.load_model_artifact.cache_clear()
    try:
        models=client.get('/api/ml/models')
        assert models.status_code==200
        assert models.json()['models'][0]['model_id']=='fixture_model'
        assert models.json()['runid_leakage_check_passed'] is True

        payload={
            'model_id':'fixture_model',
            'features':{'sensor_value':1.0},
            'feature_units':{'sensor_value':'mg/m³'},
        }
        prediction=client.post('/api/ml/predict',json=payload)
        assert prediction.status_code==200
        body=prediction.json()
        assert body['prediction']['predicted_class']=='20000+'
        assert body['prediction']['confidence_pct']==88.08
        assert body['prediction']['uncertainty_interpretation']
        assert 'not a fire prediction' in body['safety_disclaimer']
        assert client.post('/ml/predict',json={**payload,'feature_units':{'sensor_value':'°C'}}).status_code==422
        assert client.get('/api/ml/explainability/fixture_model').json()['shap_summary']
        assert client.get('/api/ml/explainability/not_registered').status_code==404
    finally:
        runtime.load_model_artifact.cache_clear()
        runtime.load_model_registry.cache_clear()


@pytest.mark.parametrize(
    ("path", "intervention", "expected_field", "expected_value"),
    [
        ("api/digital-twin/simulate", {"kind": "ventilation_cutoff"}, "airflow_cms", 0.0),
        (
            "digital-twin/simulate",
            {
                "kind": "depressurization",
                "target_o2_pct": 18,
                "target_pressure_psi": 8,
                "transition_seconds": 10,
            },
            "pressure_psi",
            8.0,
        ),
        (
            "api/digital-twin/simulate",
            {
                "kind": "inert_gas",
                "target_o2_pct": 17,
                "inert_species": "CO2",
                "transition_seconds": 10,
            },
            "o2_pct",
            17.0,
        ),
        (
            "digital-twin/simulate",
            {"kind": "gravity_shift", "target_gravity_g": 0, "transition_seconds": 10},
            "gravity_g",
            0.0,
        ),
    ],
)
def test_digital_twin_simulation_is_a_disclosed_boundary_scenario(
    path, intervention, expected_field, expected_value
):
    response = client.post(
        f"/{path}",
        json={
            "baseline": {
                "oxygen_pct": 21,
                "pressure_psi": 14.7,
                "airflow_cms": 10,
                "gravity_g": 1,
                "temp_k": 300,
                "flame_volume_m3": 0.001,
            },
            "intervention": intervention,
            "duration_seconds": 20,
        },
    )
    assert response.status_code == 200
    body = response.json()
    baseline = body["baseline_trajectory"]
    changed = body["intervention_trajectory"]
    assert len(baseline) == len(changed) == 60
    assert baseline[0]["time"] == changed[0]["time"] == 0
    assert baseline[-1]["time"] == changed[-1]["time"] == 20
    assert {"time", "temp_k", "flame_volume", "o2_pct"} <= baseline[0].keys()
    assert changed[-1][expected_field] == expected_value
    assert all(point["temp_k"] == 300 for point in changed)
    assert all(point["flame_volume"] == 0.001 for point in changed)
    assert body["model"]["validated"] is False
    assert body["model"]["calibrated"] is False
    assert "PSI-25 BASS-II" in body["scientific_references"]
    assert "PSI-69 FLEX" in body["scientific_references"]
    assert any("No numeric uncertainty margin" in item for item in body["assumptions_and_uncertainty"])
    assert body["safety_disclaimer"] == (
        "EXPLORATORY SIMULATION ONLY. Do not use for operational spacecraft hardware actuation. "
        "This boundary-condition scenario is not a validated fire, extinction, or safety prediction."
    )


def test_digital_twin_rejects_missing_inert_targets():
    response = client.post(
        "/api/digital-twin/simulate",
        json={
            "baseline": {
                "oxygen_pct": 21,
                "pressure_psi": 14.7,
                "airflow_cms": 10,
                "gravity_g": 1,
            },
            "intervention": {"kind": "inert_gas"},
            "duration_seconds": 30,
        },
    )
    assert response.status_code == 422


def test_decision_support_synthesizes_evidence_without_inventing_predictions():
    response = client.post(
        "/api/decision-support/synthesize",
        json={
            "scenario": {
                "mission": "ISS Pyrell screening",
                "gravity": "Microgravity",
                "gravity_g": 0,
                "oxygen_pct": 21,
                "pressure_psi": 14.7,
                "airflow_cms": 10,
                "material": "Pyrell",
                "pillar": "Detection",
            },
            "telemetry_state": {
                "data_label": "SYNTHETIC",
                "active_anomalies": [
                    {
                        "alert_id": "test-alert-1",
                        "severity": "CAUTION",
                        "what_changed": "Synthetic test alert",
                        "trigger_variables": ["temp_c"],
                    }
                ],
            },
            "digital_twin_state": {
                "baseline_trajectory": [{"time": 0, "o2_pct": 21}],
                "intervention_trajectory": [{"time": 0, "o2_pct": 18}],
                "assumptions_and_uncertainty": ["Scenario targets were user supplied."],
                "safety_disclaimer": "Exploratory only.",
            },
            "ml_state": {
                "prediction": {"predicted_class": "20k+"},
                "model_id": "local_fixture",
                "validation_metrics": {"accuracy": 0.5},
            },
        },
    )
    assert response.status_code == 200
    body = response.json()
    assert body["relevance_ranking"]
    assert any(item["psi_id"] == "PSI-101" for item in body["relevance_ranking"])
    assert body["active_scenario_context"]["mission"] == "ISS Pyrell screening"
    assert "telemetry_state" not in body["active_scenario_context"]
    assert body["anomaly_analysis"]["alert_count"] == 1
    assert body["anomaly_analysis"]["source_mode"] == "SYNTHETIC"
    assert body["ml_insights"]["status"] == "caller_provided"
    assert body["ml_insights"]["prediction"]["predicted_class"] == "20k+"
    assert body["intervention_comparison"]["baseline_trajectory"][0]["o2_pct"] == 21
    assert body["evidence_gaps"]
    assert body["supporting_citations"]
    assert body["epistemic_separation"]["generated_llm_suggestions"]["status"] == "not_generated"
    assert body["epistemic_separation"]["generated_llm_suggestions"]["items"] == []
    assert "No fire-safety determination" in body["safety_disclaimer"]
    assert "not a safety rating" in body["relevance_ranking"][0]["interpretation"]


def test_decision_support_reports_missing_subsystem_inputs_and_validates_scenario():
    response = client.post(
        "/decision-support/synthesize",
        json={"scenario": {"mission": "No measurements", "gravity": "Unknown"}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["anomaly_analysis"]["status"] == "not_provided"
    assert body["ml_insights"]["status"] == "not_provided"
    assert body["intervention_comparison"]["status"] == "not_provided"
    assert body["epistemic_separation"]["calculated_surrogates"]["physics"] is None
    assert client.post(
        "/api/decision-support/synthesize",
        json={"scenario": {"oxygen_pct": 101}},
    ).status_code == 422

