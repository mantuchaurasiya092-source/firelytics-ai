import csv
import io

from src.catalogue import load_catalogue, rank_studies
from src.reporting import ranking_csv, ranking_html
from src.samer import load_and_validate
from recover_phase_lineage import RAW, RUN_FILES


def test_four_nasa_psi_records_have_provenance_and_processing_status():
    studies=load_catalogue()
    original={'PSI-101','PSI-98','PSI-25','PSI-69'}
    assert original.issubset({x['psi_id'] for x in studies})
    assert len(studies)==14
    for x in (x for x in studies if x['psi_id'] in original):
        assert x['doi'].startswith('10.')
        assert x['source_url'].startswith('https://psi.nasa.gov/')
        assert x['doi_url']=='https://doi.org/'+x['doi']
        assert x['license']=='CC0-1.0 (NASA PSI record metadata)'
        assert x['local_data_status']
    assert all('hardware_rack' in x and 'fuel_phase' in x and 'predictive_variables' in x for x in studies)
    assert all(k in x for x in studies for k in ('o2_range_pct','pressure_range_psi','airflow_range_cm_s','gravity_regimes','earth_spinoff','historical_incident_links'))
    assert next(x for x in studies if x['psi_id']=='PSI-101')['local_data_status'].startswith('Locally analyzed')
    assert all(x['local_data_status'].startswith('Catalog only') for x in studies if x['psi_id']!='PSI-101')
    by_id={x['psi_id']:x for x in studies}
    assert by_id['PSI-101']['name']=='Smoke Aerosol Measurement Experiment-Reflight(SAME-R)'
    assert by_id['PSI-98']['name']=='Spacecraft Fire Safety Experiment-I(SAFFIRE-I)'
    assert by_id['PSI-25']['name']=='Burning and Suppression of Solids - II(BASS-II)'
    assert by_id['PSI-69']['name']=='Flame Extinguishment Experiment(FLEX)'
    assert all(x['research_area']=='Combustion Science' for x in studies)
    assert by_id['PSI-98']['airflow_range_cm_s']==[20,20]
    assert '75% cotton' in by_id['PSI-98']['fuel_or_sample']
    assert by_id['PSI-25']['airflow_range_cm_s'] is None and by_id['PSI-25']['airflow_max_cm_s']==40
    assert by_id['PSI-69']['pressure_range_atm']==[0.5,1.5]
    assert by_id['PSI-101']['oxygen_comparison'] is None and by_id['PSI-101']['pressure_range_atm'] is None
    assert all('NASA PSI record' in x['raw_data_availability'] for x in studies)


def test_scenario_changes_rank_and_unknowns_remain_unknown():
    studies=load_catalogue()
    iss={'mission':'ISS environment','gravity':'Microgravity','oxygen_pct':None,'pressure_atm':None,
         'airflow_cm_s':None,'material':'Pyrell','pillar':'Detection'}
    lunar={**iss,'mission':'Lunar habitat','gravity':'Lunar partial gravity'}
    a=rank_studies(studies,iss);b=rank_studies(studies,lunar)
    assert a[0]['psi_id']=='PSI-101'
    a101=next(x for x in a if x['psi_id']=='PSI-101')
    b101=next(x for x in b if x['psi_id']=='PSI-101')
    assert a101['evidence_coverage']>b101['evidence_coverage']
    assert next(f for f in b101['ranking_factors'] if f['factor']=='Gravity regime')['status']=='Evidence gap'
    assert next(f for f in a101['ranking_factors'] if f['factor']=='Pressure')['status']=='Not compared'
    suppression={'mission':'Moon','gravity':'Lunar partial gravity','oxygen_pct':18,'pressure_atm':1.0,
                 'airflow_cm_s':35,'material':'methanol','pillar':'Suppression'}
    earth={'mission':'Earth','gravity':'Earth gravity','oxygen_pct':21,'pressure_atm':.7,
           'airflow_cm_s':20,'material':'Sibal cotton fiberglass','pillar':'Prevention'}
    r2=rank_studies(studies,suppression);r3=rank_studies(studies,earth)
    assert r2[0]['psi_id']=='PSI-69'
    assert r3[0]['psi_id']=='PSI-98'
    assert rank_studies(studies,iss)==a
    assert a[0]['match_score'] != r3[0]['match_score']


def test_lineage_replay_matches_all_archived_runs_and_source_rows():
    data=load_and_validate()
    assert len(data['validation'])==6
    assert all(all(v for k,v in row.items() if k!='run') for row in data['validation'])
    run84=[x for x in data['cycles'] if x['RunID']=='84' and 1770<=x['Cycle']<=2135]
    assert len(run84)==366
    assert sum(x['ExceptionIndicator']==1 for x in run84)==182
    assert sum(x['MixedBandIndicator'] for x in run84)==0
    source=[x for x in data['source'] if x['RunID']=='95' and x['Cycle']==8677]
    assert len(source)>=1
    assert all(str(x['DustTrakAState'])=='6' for x in source)
    assert all(str(x['DustTrakAPower'])=='1' for x in source)
    selected=source[0]
    assert selected['CSVLineNumber']==selected['SourceDataRow']+1
    with (RAW/RUN_FILES['95']).open(encoding='utf-8-sig',newline='') as f:
        raw=list(csv.DictReader(f))
    original=raw[selected['SourceDataRow']-1]
    assert float(original['DustTrakAMeasurement(MgPerM3)'])==selected['Measurement']
    assert float(original['DustTrakAAnalogMeasurement(Volts)'])==selected['Analog']


def test_csv_and_html_report_exports_are_populated_and_cited():
    scenario={'mission':'Lunar habitat','gravity':'Lunar partial gravity','oxygen_pct':None,
              'pressure_atm':None,'airflow_cm_s':None,'material':'Pyrell','pillar':'Detection'}
    ranked=rank_studies(load_catalogue(),scenario)
    same=load_and_validate()
    csv_bytes=ranking_csv(ranked,scenario,same)
    rows=list(csv.DictReader(io.StringIO(csv_bytes.decode('utf-8-sig'))))
    assert len(rows)==14
    assert rows[0]['PSI_ID']
    assert rows[0]['SourceURL'].startswith('https://psi.nasa.gov/')
    assert rows[0]['Scenario']=='Lunar habitat' and 'Research pillar:' in rows[0]['RankingExplanations']
    assert 'Run 84:' in rows[0]['SAME-R findings']
    html=ranking_html(ranked,scenario,same).decode('utf-8')
    assert '<table>' in html and 'doi.org' in html and 'not safety' in html
    assert '84</td>' in html and 'Unknown' in html


def test_streamlit_app_starts_and_renders_main_workflow():
    from streamlit.testing.v1 import AppTest
    app=AppTest.from_file('../app/streamlit_app.py',default_timeout=90).run()
    assert not app.exception
    assert any('Firelytics AI' in x.value for x in app.markdown)
    assert len(app.tabs)==6
    assert any('not inferred' in x.value for x in app.info)
    assert any('recomputed from the original local CSVs' in x.value for x in app.success)
    assert {x.label for x in app.get('download_button')} >= {
        'Download ranked table (CSV)','Export ranked report data (CSV)','Export report (HTML)'}
    app.text_input[0].set_value('SAFFIRE').run()
    assert app.selectbox[0].options==['PSI-98 · SAFFIRE-I','PSI-99 · SAFFIRE-II/III']
    app.multiselect[0].set_value(['Prevention']).run()
    assert app.selectbox[0].options==['PSI-98 · SAFFIRE-I','PSI-99 · SAFFIRE-II/III']
    next(x for x in app.selectbox if x.label=='Scenario').set_value('Lunar habitat').run()
    assert next(x for x in app.selectbox if x.label=='Scenario').value=='Lunar habitat'
    app.checkbox[0].check().run()
    oxygen=next(x for x in app.number_input if x.label=='Oxygen (vol %) ')
    assert oxygen.min==0.0 and oxygen.max==100.0
    app.number_input[0].set_value(200).run()
    assert not app.exception
    assert 0.0<=app.number_input[0].value<=100.0
