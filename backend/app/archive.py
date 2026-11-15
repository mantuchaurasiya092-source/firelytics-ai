"""Read-only access to previously reconciled PSI-101 archive products.

The source CSVs are intentionally not included because their redistribution terms
are not established. This module verifies the archived cycle ledger against its
archived checkpoints; it does not replay raw-row filters or recompute labels.
"""
from __future__ import annotations

import csv
from functools import lru_cache
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
META=ROOT/'data'/'metadata'
FILES={
 'summary':'PSI101_Pyrell_DustTrakA_PhaseSummary_2026-11-14_170034.csv',
 'exceptions':'ArchivedExceptionCycleIDs.csv',
 'mixed':'MixedCycleIDs.csv',
 'mixed_rows':'MixedCycleSourceRowRefs.csv',
 'cycles':'PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_20261114_181648.csv',
 'blocks':'PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_20261114_181648.csv',
 'lags':'PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_20261114_181648.csv',
 'models':'PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_20261114_181648.csv',
 'metrics':'PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_20261114_181648.csv',
}
RUN_IDS=('63','64','76','84','95','97')
SOURCE_FILES={
 '63':'Run_063/HKPData_gmt235_1.csv',
 '64':'Run_064/HKPData_gmt235_3.csv',
 '76':'Run_076/HKPData_gmt238_4.csv',
 '84':'Run_084/HKPData_gmt242_1.csv',
 '95':'Run_095/HKPData_gmt250_4.csv',
 '97':'Run_097/HKPData_gmt251_1.csv',
}

def read_csv(name: str) -> list[dict[str,str]]:
    path=META/FILES[name]
    with path.open(encoding='utf-8-sig',newline='') as f:
        return list(csv.DictReader(f))

def _int(v): return int(v)

@lru_cache(maxsize=1)
def get_archive() -> dict:
    absent=[str(META/filename) for filename in FILES.values() if not (META/filename).is_file()]
    if absent: raise RuntimeError('Required archived SAME-R reference is missing: '+', '.join(absent))
    summaries={r['RunID']:r for r in read_csv('summary') if r['PhaseBasis']=='RelativeCyclePhase'}
    exceptions={rid:set() for rid in RUN_IDS}
    for r in read_csv('exceptions'):
        if r['PhaseBasis']=='RelativeCyclePhase': exceptions[r['RunID']].add(_int(r['Cycle']))
    mixed={rid:set() for rid in RUN_IDS}
    for r in read_csv('mixed'): mixed[r['RunID']].add(_int(r['Cycle']))
    mixed_rows={rid:set() for rid in RUN_IDS}
    for r in read_csv('mixed_rows'): mixed_rows[r['RunID']].add((_int(r['Cycle']),_int(r['SourceDataRow'])))
    rows=read_csv('cycles')
    by_run={rid:[] for rid in RUN_IDS}
    by_cycle={rid:{} for rid in RUN_IDS}
    for row in rows:
        rid=row['RunID']
        if rid not in by_run: raise RuntimeError(f'Unexpected run in archived cycle ledger: {rid}')
        cycle=_int(row['Cycle'])
        if cycle in by_cycle[rid]: raise RuntimeError(f'Duplicate cycle key in archived ledger: Run {rid}, cycle {cycle}')
        row['Cycle']=cycle
        row['SourceRowCount']=_int(row['SourceRowCount'])
        row['MixedBandIndicator']=_int(row['MixedBandIndicator'])
        row['DuplicateCycleIndicator']=_int(row['DuplicateCycleIndicator'])
        row['DuplicateRowCount']=_int(row['DuplicateRowCount'])
        row['SourceDataRowNumbers']=[_int(x) for x in row['SourceDataRows'].split(';') if x]
        row['CSVLineNumbers']=[x+1 for x in row['SourceDataRowNumbers']]
        row['ExceptionIndicator']=None if row['ExceptionIndicator']=='' else _int(row['ExceptionIndicator'])
        by_run[rid].append(row);by_cycle[rid][cycle]=row
    metrics={r['RunID']:r for r in read_csv('metrics')}
    checks=[]
    for rid in RUN_IDS:
        if rid not in summaries or rid not in metrics: raise RuntimeError(f'Archived run checkpoint missing for {rid}')
        run=by_run[rid];summary=summaries[rid];m=metrics[rid]
        archived_ex=set(exceptions[rid])
        seq_ex={r['Cycle'] for r in run if r['ExceptionIndicator']==1}
        seq_mixed={r['Cycle'] for r in run if r['MixedBandIndicator']==1}
        seq_mixed_rows={(r['Cycle'],source) for r in run if r['MixedBandIndicator']==1 for source in r['SourceDataRowNumbers']}
        classified=sum(r['MixedBandIndicator']==0 and r['ExceptionIndicator'] in (0,1) for r in run)
        duplicates=sum(r['DuplicateCycleIndicator'] for r in run)
        cycles_sorted=sorted(r['Cycle'] for r in run)
        missing=(cycles_sorted[-1]-cycles_sorted[0]+1-len(cycles_sorted)) if cycles_sorted else 0
        gaps=sum(b-a>1 for a,b in zip(cycles_sorted,cycles_sorted[1:]))
        phase0=[r for r in run if r['RelativeCyclePhase']=='Phase0' and r['MixedBandIndicator']==0]
        phase1=[r for r in run if r['RelativeCyclePhase']=='Phase1' and r['MixedBandIndicator']==0]
        checks.append({
          'run_id':rid,
          'first_last_cycles_match':bool(run) and cycles_sorted[0]==_int(summary['FirstCycle'])==_int(m['FirstEligibleCycle']) and cycles_sorted[-1]==_int(summary['LastCycle'])==_int(m['LastEligibleCycle']),
          'classified_count_matches':classified==_int(summary['ClassifiedCycles'])==_int(m['ClassifiedBinaryCycles']),
          'exception_count_matches':len(seq_ex)==_int(summary['ExceptionCycles'])==_int(m['PhaseExceptions']),
          'exception_cycle_identities_match':seq_ex==archived_ex,
          'mixed_cycle_identities_match':seq_mixed==mixed[rid],
          'mixed_source_rows_match':seq_mixed_rows==mixed_rows[rid],
          'duplicate_cycle_count_matches':duplicates==_int(summary['DuplicateCycleNumbers'])==_int(m['DuplicateCycleNumbers']),
          'missing_cycle_count_matches':missing==_int(summary['MissingCycleNumbers'])==_int(m['MissingCycleNumbers']),
          'gap_event_count_matches':gaps==_int(summary['GapEvents'])==_int(m['GapEvents']),
          'phase_mapping_counts_match':len(phase0)==_int(summary['Phase0CycleCount']) and len(phase1)==_int(summary['Phase1CycleCount']) and all(r['ExpectedBand']==summary['Phase0DominantBand'] for r in phase0) and all(r['ExpectedBand']==summary['Phase1DominantBand'] for r in phase1),
          'eligible_cycle_record_count_matches':len(run)==_int(m['EligibleCycleRecords']),
          'mixed_exclusion_count_matches':len(seq_mixed)==_int(summary['MixedBandCycles'])==_int(m['ExcludedMixedFromBinary']),
          'cycle_ledger_unique':len(run)==_int(summary['UniqueCycles']),
        })
    if any(not all(v for k,v in c.items() if k!='run_id') for c in checks):
        raise RuntimeError('Archived SAME-R reconciliation failed; refusing to serve cycle data: '+repr(checks))
    return {'summaries':summaries,'exceptions':exceptions,'mixed':mixed,'cycles':by_run,'cycle_index':by_cycle,
            'blocks':[r for r in read_csv('blocks')], 'lags':read_csv('lags'),'models':read_csv('models'),
            'metrics':metrics,'validation':checks,'source_files':SOURCE_FILES,
            'classification_source':'archived_cycle_sequence_20261114_181648',
            'processing_status':'Verified archived output; original raw CSV replay was not performed in this deployment.',
            'raw_replay_performed':False}

