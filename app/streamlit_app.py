from __future__ import annotations
import csv, html, io, sys
from pathlib import Path
import streamlit as st

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
from src.catalogue import load_catalogue, rank_studies, REPOSITORY_SCOPE
from src.samer import load_and_validate
from src.reporting import ranking_csv, ranking_html

st.set_page_config(page_title='Firelytics AI | NASA combustion research',page_icon='🔥',layout='wide')
st.markdown('''<style>
html,body,[class*="css"]{font-family:Arial,sans-serif}.stApp{background:linear-gradient(180deg,#071522 0,#0b1c2b 270px,#f4f7fa 270px)}
.hero{padding:1.5rem 1.8rem;border:1px solid #224052;border-radius:20px;background:linear-gradient(125deg,#0d2638,#135061);color:#fff;margin-bottom:1rem}
.hero h1{font-size:2.3rem;margin:.3rem 0}.hero p{color:#d3e4ec}.pill{display:inline-block;padding:.25rem .6rem;border-radius:999px;background:#15394b;color:#a8e9d8;margin:.2rem;font-size:.8rem}
table.data{border-collapse:collapse;width:100%;font-size:.86rem;background:white}table.data th,table.data td{padding:.48rem .6rem;border-bottom:1px solid #dce6ec;text-align:left;vertical-align:top}table.data th{background:#edf4f7;position:sticky;top:0}div[data-testid="stMetric"]{background:white;border:1px solid #dce6ec;padding:.8rem;border-radius:12px}
</style>''',unsafe_allow_html=True)

def table(rows, columns=None):
    rows=list(rows)
    if not rows: st.caption('No records for this selection.'); return
    columns=columns or list(dict.fromkeys(k for r in rows for k in r))
    head=''.join(f'<th>{html.escape(str(c))}</th>' for c in columns)
    body=''.join('<tr>'+''.join(f'<td>{html.escape(str(r.get(c,"")))}</td>' for c in columns)+'</tr>' for r in rows)
    st.markdown(f'<div style="overflow:auto;max-height:520px"><table class="data"><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table></div>',unsafe_allow_html=True)

def svg_chart(rows,xkey,ykey,title,color_key=None):
    pts=[]
    for r in rows:
        try: pts.append((float(r[xkey]),float(r[ykey]),str(r.get(color_key,''))))
        except (ValueError,TypeError,KeyError): pass
    if not pts: st.caption('No numeric values to plot.'); return
    w,h=900,280;pad=42; xs=[p[0] for p in pts];ys=[p[1] for p in pts]
    xmin,xmax=min(xs),max(xs);ymin,ymax=min(ys),max(ys); yr=max(ymax-ymin,1e-12);xr=max(xmax-xmin,1)
    X=lambda v:pad+(v-xmin)/(xr)*(w-2*pad);Y=lambda v:h-pad-(v-ymin)/yr*(h-2*pad)
    palette={'10000-14999':'#188b81','15000-19999':'#3c78a8','20000+':'#cf684d','0-9999':'#aa8a2f','MixedBand':'#777'}
    grouped={}
    for x,y,c in pts:grouped.setdefault(c,[]).append((x,y))
    shapes=f'<line x1="{pad}" y1="{h-pad}" x2="{w-pad}" y2="{h-pad}" stroke="#8193a0"/><line x1="{pad}" y1="{pad}" x2="{pad}" y2="{h-pad}" stroke="#8193a0"/>'
    for c,ps in grouped.items():
        color=palette.get(c,'#236c8a');coords=' '.join(f'{X(x):.1f},{Y(y):.1f}' for x,y in ps)
        shapes+=f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.7" opacity=".85"/>'
        shapes+=''.join(f'<circle cx="{X(x):.1f}" cy="{Y(y):.1f}" r="2.7" fill="{color}"><title>Cycle {x:g}: {y:g}; {html.escape(c)}</title></circle>' for x,y in ps)
    st.markdown(f'<h4>{html.escape(title)}</h4><svg viewBox="0 0 {w} {h}" style="width:100%;background:white;border:1px solid #dce6ec;border-radius:10px">{shapes}<text x="{w/2}" y="{h-8}" text-anchor="middle" font-size="12">Cycle</text><text x="12" y="20" font-size="12">{html.escape(ykey)}</text></svg>',unsafe_allow_html=True)

@st.cache_data(show_spinner='Loading catalogue and validating archived SAME-R lineage…')
def products(): return load_catalogue(),load_and_validate()
try: catalogue,samer=products()
except Exception as exc: st.error('Evidence package validation failed.');st.exception(exc);st.stop()

st.markdown(f'''<div class="hero"><div class="pill">NASA PSI catalogue</div><div class="pill">{len(catalogue)} DOI-verified investigations</div><div class="pill">{REPOSITORY_SCOPE['total_investigations']} PSI combustion studies · {REPOSITORY_SCOPE['aggregate_telemetry_label']}</div><div class="pill">SAME-R local analysis</div><h1>Firelytics AI</h1><p>Explore NASA combustion investigations and compare documented evidence with a mission scenario. Matching is a research relevance aid, not a safety rating.</p></div>''',unsafe_allow_html=True)

st.sidebar.markdown('### Mission scenario')
mission=st.sidebar.selectbox('Scenario',['ISS environment','Lunar habitat','Pressurised rover','Mars habitat','Custom scenario'])
gravity={'ISS environment':'Microgravity','Lunar habitat':'Lunar partial gravity','Mars habitat':'Mars partial gravity'}.get(mission)
if mission=='Pressurised rover': gravity='Lunar partial gravity' if st.sidebar.selectbox('Rover destination',['Moon','Mars'])=='Moon' else 'Mars partial gravity'
if mission=='Custom scenario':gravity=st.sidebar.selectbox('Gravity regime',['Unknown','Microgravity','Lunar partial gravity','Mars partial gravity','Earth gravity'])
def numeric(label,enabled,default,lo,hi,step):return st.sidebar.number_input(label,min_value=lo,max_value=hi,value=default,step=step,disabled=not enabled) if enabled else None
o2=numeric('Oxygen (vol %) ',st.sidebar.checkbox('Specify oxygen concentration'),21.,0.,100.,.5)
pressure=numeric('Pressure (atm)',st.sidebar.checkbox('Specify pressure'),1.,.01,20.,.1)
airflow=numeric('Airflow (cm/s)',st.sidebar.checkbox('Specify airflow'),20.,0.,200.,1.)
material=st.sidebar.text_input('Material or fuel (optional)',placeholder='cotton, Pyrell, methanol')
pillar=st.sidebar.selectbox('Research pillar',['Any pillar','Prevention','Detection','Suppression'])
scenario={'mission':mission,'gravity':gravity,'oxygen_pct':o2,'pressure_atm':pressure,'airflow_cm_s':airflow,'material':material,'pillar':pillar}
ranked=rank_studies(catalogue,scenario)
tabs=st.tabs(['Overview','Investigation explorer','Scenario ranking','Evidence explorer','SAME-R analysis','Scientific report'])

with tabs[0]:
 st.subheader('Evidence landscape');cols=st.columns(4)
 vals=[len(catalogue),3,sum('Locally analyzed' in x['local_data_status'] for x in catalogue),sum(x['local_data_status'].startswith('Catalog only') for x in catalogue)]
 for c,label,v in zip(cols,['NASA PSI investigations','Fire-safety pillars','Locally analyzed studies','Catalog-only studies'],vals):c.metric(label,v)
 st.markdown(f'**Current scenario:** {mission} · {gravity} · {pillar}')
 st.markdown(f"**PSI repository scope:** {REPOSITORY_SCOPE['total_investigations']} combustion investigations · {REPOSITORY_SCOPE['aggregate_telemetry_label']} aggregate telemetry · {REPOSITORY_SCOPE['deeply_indexed_count']} deeply indexed + {REPOSITORY_SCOPE['associated_count']} associated.")
 with st.expander('PSI Repository Coverage & Scope Matrix (24 investigations · ~12.4 TB)'):
  st.write(REPOSITORY_SCOPE['summary']);st.caption(REPOSITORY_SCOPE['id_reconciliation'])
  st.markdown('**Tier 1 — deeply indexed**');table([{'PSI ID':x['psi_id'],'Investigation':x['short_name'],'Focus':x['focus']} for x in REPOSITORY_SCOPE['tier1']])
  st.markdown('**Tier 2 — associated PSI studies (repository completeness)**');table([{'Study':x['name'],'Focus':x['focus']} for x in REPOSITORY_SCOPE['tier2']])
  for mission_scope in REPOSITORY_SCOPE['upcoming_missions']:st.markdown(f"**{mission_scope['key']}** · {mission_scope['name']} — {mission_scope['bounding']}")
  st.caption(REPOSITORY_SCOPE['bounding_statement']);st.caption(' '.join(REPOSITORY_SCOPE['limitations']))
 st.markdown('#### Research pillar coverage')
 table([{'Pillar':p,'Investigations':', '.join(x['short_name'] for x in catalogue if p in x['pillars'])} for p in ['Prevention','Detection','Suppression']])
 st.info('Only the local SAME-R Pyrell subset is processed. Partial-gravity results are not inferred from microgravity studies. The challenge requests an interactive, SI-powered research dashboard; no external SI model is configured here, so summaries and ranking are deterministic and source-linked.')

with tabs[1]:
 st.subheader('Investigation explorer');q=st.text_input('Search records',placeholder='Name, fuel, sensor, objective, DOI');selected=st.multiselect('Filter by pillar',['Prevention','Detection','Suppression'])
 shown=[x for x in catalogue if q.lower() in ' '.join(str(x.get(k,'')) for k in ('psi_id','name','objective','fuel_or_sample','sensors_variables','tags','doi')).lower() and (not selected or set(selected).intersection(x['pillars']))]
 st.caption(f'{len(shown)} investigation(s) match.');choice=st.selectbox('Investigation',[x['psi_id']+' · '+x['short_name'] for x in shown] or ['No results'])
 if shown:
  x=next(x for x in shown if x['psi_id']==choice.split(' · ')[0]);st.markdown(f"### {x['short_name']} · {x['name']}");st.write(x['objective']);st.write('**Sample/fuel:** '+x['fuel_or_sample']);st.write('**Platform:** '+x['platform']+' · '+x['hardware']);st.write('**Sensors:** '+x['sensors_variables']);st.write('**Conditions:** O₂ '+x['oxygen_recorded']+'; pressure '+x['pressure_recorded']+'; airflow '+x['airflow_recorded']);st.write('**NASA source description:** '+x['source_objective_verbatim']);st.write('**Research context:** '+x['source_findings']);st.markdown(f"[NASA PSI record]({x['source_url']}) · [DOI {x['doi']}]({x['doi_url']}) · {x['license']}")

with tabs[2]:
 st.subheader('Investigation ranking');st.caption('Similarity uses only documented comparable factors. Evidence coverage is separate. Neither is a safety rating.')
 rankrows=[{'Rank':i+1,'PSI ID':x['psi_id'],'Investigation':x['short_name'],'Match score %':round(x['match_score'],1),'Evidence coverage %':round(x['evidence_coverage'],1),'Local raw data processed':x['local_data_status'].startswith('Locally analyzed')} for i,x in enumerate(ranked)]
 table(rankrows);st.download_button('Download ranked table (CSV)',ranking_csv(ranked,scenario,samer),file_name='firelytics_scenario_ranking.csv',mime='text/csv')
 for i,x in enumerate(ranked,1):
  with st.expander(f"#{i} {x['short_name']} · {x['match_score']:.1f}% similarity · {x['evidence_coverage']:.1f}% coverage",expanded=i==1):
   st.write(x['objective']);table([{'Factor':f['factor'],'Result':f['status'],'Evidence/reason':f['explanation'],'Score':f['score']} for f in x['ranking_factors']]);st.caption(x['source_url']+' · '+x['doi_url'])

with tabs[3]:
 st.subheader('Evidence explorer');st.write('Source metadata stays separate from local derived comparisons. Unknown values remain unknown.')
 table([{'PSI ID':x['psi_id'],'Name':x['short_name'],'DOI':x['doi'],'Pillars':', '.join(x['pillars']),'Sample':x['fuel_or_sample'],'Platform':x['platform'],'Oxygen':x['oxygen_recorded'],'Pressure':x['pressure_recorded'],'Airflow':x['airflow_recorded'],'Sensors':x['sensors_variables'],'Local status':x['local_data_status'],'License':x['license']} for x in catalogue])
 st.markdown('**Applicability limits:** PSI overview records lack comparable numeric conditions for every study. BASS-II apparatus capacity is not a tested condition. Partial-gravity fire behavior is a research gap. Catalog-only source files have not been locally processed.')
 for x in catalogue:st.markdown(f"**{x['psi_id']}** · [NASA PSI]({x['source_url']}) · [DOI {x['doi']}]({x['doi_url']}) · {x['license']}")

with tabs[4]:
 st.subheader('SAME-R · local smoke/aerosol analysis');st.info('Phase exceptions are classification mismatches in archived DustTrak cycles. They are not recorded fires, alarms, or proof of hazards.')
 st.success('Cycle classifications are recomputed from the original local CSVs using the recovered historical logic, then checked against archived summaries, exception identities, mixed-band rows and duplicate counts. This is lineage reproducibility, not independent scientific validation.')
 table(samer['validation']);run=st.selectbox('Run',['84','95','63','64','76','97'])
 rc=[x for x in samer['cycles'] if x['RunID']==run];lo=min(x['Cycle'] for x in rc);hi=max(x['Cycle'] for x in rc)
 start,end=st.slider('Cycle range',lo,hi,(lo,hi),key='range_'+run);view=[x for x in rc if start<=x['Cycle']<=end]
 c1,c2,c3=st.columns(3);c1.metric('Classified cycles',sum(x['MixedBandIndicator']==0 for x in view));c2.metric('Phase exceptions',sum(x['ExceptionIndicator']==1 for x in view));c3.metric('Mixed cycles excluded',sum(x['MixedBandIndicator']==1 for x in view))
 st.caption('Recovered four-band classification and archived per-run mapping. Mixed-band cycles remain separate from binary exceptions.')
 svg_chart(view,'Cycle','CycleMedianMeasurement',f'Run {run}: DustTrak A cycle measurements','ObservedBand');svg_chart(view,'Cycle','CycleMedianAnalog',f'Run {run}: DustTrak A analog channel','ObservedBand')
 table([x for x in samer['run_metrics'] if str(x['RunID'])==run])
 if run in ('84','95'):
  st.markdown('#### Episode/control comparisons');table([x for x in samer['analog_comparison'] if f'Run{run}_Episode' in x.get('Comparison','')])
 st.markdown('#### Original eligible source rows');cycles=sorted({x['Cycle'] for x in rc});selected_cycle=st.selectbox('Cycle number',cycles,key='source_'+run)
 source=[x for x in samer['source'] if x['RunID']==run and x['Cycle']==selected_cycle]
 cols=['SourceDataRow','CSVLineNumber','TimeString','Cycle','ClassifiedBand','Measurement','Analog','DustTrakAState','DustTrakAPower','RunMode','TestNumber','ExpectedBand','ObservedBand','ExceptionIndicator']
 table(source,[c for c in cols if c in source[0]])
 out=io.StringIO(newline='');w=csv.DictWriter(out,fieldnames=list(source[0]));w.writeheader();w.writerows(source)
 st.download_button('Download selected original rows',out.getvalue().encode(),file_name=f'PSI101_Run{run}_Cycle{selected_cycle}_source_rows.csv',mime='text/csv')

with tabs[5]:
 st.subheader('Scientific report');st.write('Deterministic evidence summary; no external SI model is configured. Claims link to NASA PSI and DOI records.')
 st.markdown(f'### Scenario\n{mission} · {gravity} · O₂ {o2 if o2 is not None else "unspecified"} · pressure {pressure if pressure is not None else "unspecified"} atm · airflow {airflow if airflow is not None else "unspecified"} cm/s · material {material or "unspecified"} · {pillar}')
 st.markdown('### Ranked evidence')
 for i,x in enumerate(ranked,1):st.markdown(f"**{i}. {x['psi_id']} {x['short_name']}** — {x['match_score']:.1f}% similarity; {x['evidence_coverage']:.1f}% evidence coverage. {x['objective']} [NASA PSI]({x['source_url']}) · [DOI]({x['doi_url']})")
 st.markdown('### Limitations');st.write('Only PSI-101 Pyrell source runs in this repository have been processed. Other records are catalogue entries. Unknown conditions remain unknown. Partial-gravity extrapolation and safety verdicts are not made. SAME-R exceptions are analysis observations only.')
 st.download_button('Export ranked report data (CSV)',ranking_csv(ranked,scenario,samer),file_name='firelytics_scientific_report.csv',mime='text/csv');st.download_button('Export report (HTML)',ranking_html(ranked,scenario,samer),file_name='firelytics_scientific_report.html',mime='text/html')
st.markdown('---');st.caption('Independent research prototype; not endorsed by NASA and not an operational fire-safety system.')
