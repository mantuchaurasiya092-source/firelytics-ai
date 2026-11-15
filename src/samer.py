"""Read-only SAME-R loader with historical lineage and periodicity cross-checks."""
from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path

from recover_phase_lineage import (
    BANDS, MIXED_ROWS, MIXED_SUMMARY, PHASE_EXCEPTIONS, PHASE_SUMMARY,
    RAW, RUN_FILES, band, number,
)

ROOT = Path(__file__).resolve().parents[1]
SEQUENCE_PATH = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv'
BLOCK_PATH = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_20261114_181648.csv'
LAG_PATH = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_181648.csv'
MODEL_PATH = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_181648.csv'
RUN_METRICS_PATH = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_181648.csv'
REVERSAL_REPORT = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_PhaseReversal_CorrelationAuditReport_20261114_183955.txt'
REVERSAL_METRICS = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_PhaseReversal_EpisodeControlMetrics_20261114_183955.csv'
REVERSAL_INTERVALS = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_PhaseReversal_TimestampCycleIntervals_20261114_183955.csv'
REVERSAL_ANALOG = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_PhaseReversal_AnalogMeasurementComparison_20261114_183955.csv'
REVERSAL_ROWS = ROOT / 'data/metadata/PSI101_Pyrell_DustTrakA_PhaseReversal_TransitionAlignedRows_20261114_183955.csv'


def _csv(path: Path) -> list[dict]:
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def load_and_validate() -> dict:
    """Replay the recovered eligibility/classification and cross-check immutable products."""
    required=[SEQUENCE_PATH,BLOCK_PATH,LAG_PATH,MODEL_PATH,RUN_METRICS_PATH,
              REVERSAL_REPORT,REVERSAL_METRICS,REVERSAL_INTERVALS,REVERSAL_ANALOG,REVERSAL_ROWS]
    missing=[str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError('Required validated SAME-R product(s) are missing: '+', '.join(missing))
    archived_summary={r['RunID']:r for r in _csv(PHASE_SUMMARY) if r['PhaseBasis']=='RelativeCyclePhase'}
    archived_ex=defaultdict(set)
    for r in _csv(PHASE_EXCEPTIONS):
        if r['PhaseBasis']=='RelativeCyclePhase':archived_ex[r['RunID']].add(int(r['Cycle']))
    archived_mixed=defaultdict(set)
    for r in _csv(MIXED_SUMMARY):archived_mixed[r['RunID']].add(int(r['Cycle']))
    archived_mixed_rows=defaultdict(set)
    for r in _csv(MIXED_ROWS):archived_mixed_rows[r['RunID']].add((int(r['Cycle']),int(r['SourceDataRow'])))
    seqrows=_csv(SEQUENCE_PATH)
    saved=defaultdict(dict)
    for r in seqrows:saved[r['RunID']][int(r['Cycle'])]=r
    all_selected=[]; cycle_rows=[]; checks=[]
    for rid,rel in RUN_FILES.items():
        source=RAW/rel
        with source.open(encoding='utf-8-sig',newline='') as f: raw=list(csv.DictReader(f))
        selected=[]
        for i,row in enumerate(raw,1):
            if str(row.get('TestNumber','')).strip()!=rid:continue
            if str(row.get('RunMode','')).strip()!='3':continue
            if str(row.get('DustTrakAState','')).strip()!='6':continue
            if str(row.get('DustTrakAPower','')).strip()!='1':continue
            m=number(row.get('DustTrakAMeasurement(MgPerM3)'));a=number(row.get('DustTrakAAnalogMeasurement(Volts)'));c=number(row.get('CycleCounter'))
            if m is None or a is None or c is None or m==-999 or c!=int(c):continue
            selected.append({'RunID':rid,'Cycle':int(c),'SourceDataRow':i,'CSVLineNumber':i+1,
                             'Measurement':m,'Analog':a,'ClassifiedBand':band(m),'TimeString':row.get('TimeString',''),
                             'Time':number(row.get('Time')),'RawRow':row,**row})
        all_selected.extend(selected)
        grouped=defaultdict(list)
        for x in selected:grouped[x['Cycle']].append(x)
        arc=archived_summary[rid];first=int(arc['FirstCycle']);reconstructed_ex=set();reconstructed_mixed=set();mixed_sources=set();bad=[]
        for c,group in grouped.items():
            bands={x['ClassifiedBand'] for x in group};obs=next(iter(bands)) if len(bands)==1 else 'MixedBand'
            phase='Phase0' if (c-first)%2==0 else 'Phase1'
            expected=arc['Phase0DominantBand'] if phase=='Phase0' else arc['Phase1DominantBand']
            flag=int(obs!='MixedBand' and obs!=expected) if obs!='MixedBand' else ''
            if flag==1:reconstructed_ex.add(c)
            if obs=='MixedBand':
                reconstructed_mixed.add(c);mixed_sources.update((c,x['SourceDataRow']) for x in group)
            savedrow=saved[rid].get(c)
            if (savedrow is None or savedrow['ObservedBand']!=obs or savedrow['ExpectedBand']!=expected or
                int(savedrow['SourceRowCount'])!=len(group) or str(savedrow['ExceptionIndicator'])!=str(flag)):
                bad.append(c)
            cycle_rows.append({'RunID':rid,'Cycle':c,'RelativeCyclePhase':phase,'ExpectedBand':expected,
                               'ObservedBand':obs,'ExceptionIndicator':flag,'MixedBandIndicator':int(obs=='MixedBand'),
                               'SourceRowCount':len(group),'DuplicateCycleIndicator':int(len(group)>1),
                               'SourceDataRows':';'.join(str(x['SourceDataRow']) for x in group),
                               'FirstTimestamp':group[0]['TimeString'],'LastTimestamp':group[-1]['TimeString'],
                               'CycleMedianMeasurement':statistics.median([x['Measurement'] for x in group]),
                               'CycleMedianAnalog':statistics.median([x['Analog'] for x in group])})
        classified=sum(len({x['ClassifiedBand'] for x in grouped[c]})==1 for c in grouped)
        duplicate=sum(len(g)>1 for g in grouped.values())
        checks.append({'run':rid,'sequence_matches':not bad,'classified_matches':classified==int(arc['ClassifiedCycles']),
                       'exceptions_match':len(reconstructed_ex)==int(arc['ExceptionCycles']) and reconstructed_ex==archived_ex[rid],
                       'mixed_matches':reconstructed_mixed==archived_mixed[rid] and mixed_sources==archived_mixed_rows[rid],
                       'duplicates_match':duplicate==int(arc['DuplicateCycleNumbers'])})
    if any(not all(v for k,v in c.items() if k!='run') for c in checks):
        raise ValueError('SAME-R validation failed: '+repr(checks))
    cycle_rows.sort(key=lambda x:(x['RunID'],x['Cycle']))
    all_selected.sort(key=lambda x:(x['RunID'],x['SourceDataRow']))
    cycle_index={(x['RunID'],x['Cycle']):x for x in cycle_rows}
    for row in all_selected:
        cycle=cycle_index[(row['RunID'],row['Cycle'])]
        for key in ('ExpectedBand','ObservedBand','ExceptionIndicator','MixedBandIndicator'):
            row[key]=cycle[key]
    return {
        'validation':checks,'cycles':cycle_rows,'source':all_selected,
        'blocks':_csv(BLOCK_PATH), 'lags':_csv(LAG_PATH),
        'models':_csv(MODEL_PATH), 'run_metrics':_csv(RUN_METRICS_PATH),
        'reversal_metrics':_csv(REVERSAL_METRICS), 'intervals':_csv(REVERSAL_INTERVALS),
        'analog_comparison':_csv(REVERSAL_ANALOG), 'transition_rows':_csv(REVERSAL_ROWS),
        'periodicity_sequence_path':SEQUENCE_PATH,'reversal_report_path':REVERSAL_REPORT,
    }
