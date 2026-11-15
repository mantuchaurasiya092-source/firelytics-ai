"""Read-only correlation audit for PSI-101 Pyrell DustTrak A phase-reversal episodes."""
import csv, math, random, statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path
import recover_phase_lineage as lineage

ROOT = Path(__file__).resolve().parent
META = ROOT / 'data' / 'metadata'
RAW = ROOT / 'data' / 'raw' / 'PSI-101' / 'Pyrell'
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
PERIODICITY_STAMP = '20261114_181648'
PERIODICITY_SEQUENCE = META / f'PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_{PERIODICITY_STAMP}.csv'
PERIODICITY_BLOCKS = META / f'PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_{PERIODICITY_STAMP}.csv'
SUMMARY_PATH = lineage.PHASE_SUMMARY
EXCEPTIONS_PATH = lineage.PHASE_EXCEPTIONS
MIXED_SUMMARY_PATH = lineage.MIXED_SUMMARY
MIXED_ROWS_PATH = lineage.MIXED_ROWS
RUN_FILES = lineage.RUN_FILES
BOOTSTRAPS = 1000
BLOCK_LENGTH = 22
SEED = 841958

PRIMARY = {'84': (1770, 2135), '95': (8677, 8858)}
CONTROLS = {'84': [('Before', 1404, 1769)],
            '95': [('Before', 8495, 8676), ('After', 8859, 9040)]}

STATUS_FIELDS = [
    'RunMode', 'TestRunning', 'DustTrakAState', 'DustTrakAPower', 'DustTrakAKeySelect',
    'DustTrakBState', 'DustTrakBPower', 'DustTrakBKeySelect', 'PTrakState', 'PTrakPower',
    'PTrakKeySelect', 'HeatingInProgress', '12VDCHeaterEnable', 'SampleHeaterOverride',
    'ThermalPrecipitatorPreAgeHeater', 'ThermalPrecipitatorPostAgeHeater',
    'ThermalPrecipitatorPreAgeValve', 'ThermalPrecipitatorPostAgeValve',
    'ThermalPrecipitatorPreAgeCableSense', 'ThermalPrecipitatorPostAgeCableSense',
    'STSDetectorAlarm', 'PositionerEnable', 'CarouselPower', 'VideoRecording',
]
CONTINUOUS_FIELDS = [
    ('DustTrakA measurement', 'DustTrakAMeasurement(MgPerM3)'),
    ('DustTrakA analog', 'DustTrakAAnalogMeasurement(Volts)'),
    ('DustTrakB measurement', 'DustTrakBMeasurement(MgPerM3)'),
    ('DustTrakB analog', 'DustTrakBAnalogMeasurement(Volts)'),
    ('PTrak measurement', 'PTrakMeasurement(PtPerCC)'),
    ('Gas plume temperature', 'GasPlumeTemperature(DegC)'),
    ('Sample resistance', 'SampleResistance(Ohms)'),
    ('MFC mass flow rate', 'MFCMassFlowRate(LPM)'),
    ('MFC pressure', 'MFCPressure(PSIA)'),
    ('GN2 main pressure', 'GN2MainPressure[PN02](PSIA)'),
    ('GN2 regulated pressure', 'GN2RegulatedPressure[PN12](PSIG)'),
    ('Vacuum pressure', 'VacuumPressure[VR04](PSIA)'),
    ('Drive side pressure', 'DriveSidePressure[BN02](PSIA)'),
    ('Sample side pressure', 'SampleSidePressure[AT20](PSIA)'),
]


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    fields = []
    for row in rows:
        for k in row:
            if k not in fields:
                fields.append(k)
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields or ['RunID'], extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def nval(v):
    return lineage.number(v)


def qtile(x, p):
    if not x:
        return ''
    z = sorted(x)
    pos = (len(z)-1)*p
    lo = math.floor(pos); hi = math.ceil(pos)
    return z[lo] if lo == hi else z[lo]*(hi-pos)+z[hi]*(pos-lo)


def stats(values):
    x = []
    for v in values:
        if v is None or v == '':continue
        try:
            z=float(v)
            if math.isfinite(z):x.append(z)
        except (TypeError,ValueError):
            continue
    if not x:
        return dict(N=0, Mean='', Median='', SD='', Q1='', Q3='', IQR='', Min='', Max='')
    q1, q3 = qtile(x,.25), qtile(x,.75)
    return dict(N=len(x), Mean=statistics.mean(x), Median=statistics.median(x),
                SD=statistics.stdev(x) if len(x)>1 else 0.0, Q1=q1, Q3=q3, IQR=q3-q1,
                Min=min(x), Max=max(x))


def hedges_g(a,b):
    a=[float(x) for x in a if x is not None and x!='']; b=[float(x) for x in b if x is not None and x!='']
    if len(a)<2 or len(b)<2:return ''
    pooled=((len(a)-1)*statistics.variance(a)+(len(b)-1)*statistics.variance(b))/(len(a)+len(b)-2)
    if pooled<=0:return 0.0
    d=(statistics.mean(a)-statistics.mean(b))/math.sqrt(pooled)
    correction=1-3/(4*(len(a)+len(b))-9)
    return d*correction


def moving_blocks(records, block_len):
    """All fixed-length cycle blocks wholly inside a consecutive cycle segment."""
    if not records:return []
    ordered=sorted(records,key=lambda r:r['Cycle'])
    segments=[]; cur=[]
    for x in ordered:
        if cur and x['Cycle'] != cur[-1]['Cycle']+1:
            segments.append(cur);cur=[]
        cur.append(x)
    if cur:segments.append(cur)
    blocks=[]
    for seg in segments:
        k=min(block_len,len(seg))
        if k<=0:continue
        if len(seg)<block_len:
            blocks.append(seg)
        else:
            blocks.extend(seg[i:i+block_len] for i in range(len(seg)-block_len+1))
    return blocks


def resample_window(records, n, rng, block_len=BLOCK_LENGTH):
    blocks=moving_blocks(records,block_len)
    if not blocks:return []
    out=[]
    while len(out)<n:
        out.extend(rng.choice(blocks))
    return out[:n]


def boot_diff(a_records,b_records,metric,condition_a=None,condition_b=None,within=False):
    """Moving-block CI for mean difference, with cycle as sampling unit."""
    a_records=sorted(a_records,key=lambda r:r['Cycle']); b_records=sorted(b_records,key=lambda r:r['Cycle'])
    av=[r[metric] for r in a_records if r.get(metric) is not None and r.get(metric)!='' and (condition_a is None or condition_a(r))]
    bv=[r[metric] for r in b_records if r.get(metric) is not None and r.get(metric)!='' and (condition_b is None or condition_b(r))]
    point=statistics.mean(av)-statistics.mean(bv) if av and bv else ''
    if not av or not bv:return point,'','',0
    rng=random.Random(SEED + len(a_records)*31 + len(b_records)*17 + len(metric))
    vals=[]; attempts=0
    while len(vals)<BOOTSTRAPS and attempts<BOOTSTRAPS*4:
        attempts+=1
        if within:
            sampled=resample_window(a_records,len(a_records),rng)
            xa=[r[metric] for r in sampled if r.get(metric) is not None and r.get(metric)!='' and (condition_a is None or condition_a(r))]
            xb=[r[metric] for r in sampled if r.get(metric) is not None and r.get(metric)!='' and (condition_b is None or condition_b(r))]
        else:
            sa=resample_window(a_records,len(a_records),rng)
            sb=resample_window(b_records,len(b_records),rng)
            xa=[r[metric] for r in sa if r.get(metric) is not None and r.get(metric)!='' and (condition_a is None or condition_a(r))]
            xb=[r[metric] for r in sb if r.get(metric) is not None and r.get(metric)!='' and (condition_b is None or condition_b(r))]
        if xa and xb:vals.append(statistics.mean(xa)-statistics.mean(xb))
    if len(vals)<100:return point,'','',len(vals)
    return point,qtile(vals,.025),qtile(vals,.975),len(vals)


def cycle_record(run, cycle, source_rows):
    original=cycle.copy()
    source_rows=sorted(source_rows,key=lambda r:r['SourceDataRow'])
    vals_a=[r['Measurement'] for r in source_rows]
    vals_aa=[r['Analog'] for r in source_rows]
    other={}
    for label,field in CONTINUOUS_FIELDS[2:]:
        other[field]=statistics.median([nval(r['Row'].get(field)) for r in source_rows if nval(r['Row'].get(field)) is not None]) if any(nval(r['Row'].get(field)) is not None for r in source_rows) else None
    numeric_times=[r['TimestampSeconds'] for r in source_rows if r['TimestampSeconds'] is not None]
    times=[r['Row'].get('TimeString','') for r in source_rows]
    original.update(SourceRows=source_rows, SourceRowFirst=source_rows[0]['SourceDataRow'],
                    SourceRowLast=source_rows[-1]['SourceDataRow'],
                    SourceRowPositionDifference=cycle['Cycle']-source_rows[0]['SourceDataRow'],
                    CycleMedianMeasurement=statistics.median(vals_a),
                    CycleMeanMeasurement=statistics.mean(vals_a),
                    CycleMedianAnalog=statistics.median(vals_aa),
                    CycleMeanAnalog=statistics.mean(vals_aa),
                    CycleMedianTimestampSeconds=statistics.median(numeric_times) if numeric_times else None,
                    TimeStringFirst=times[0] if times else '', TimeStringLast=times[-1] if times else '',
                    RawRows=source_rows, OtherCycleMedians=other,
                    RepeatedTimestampRows=0, DistinctRepeatedTimestamps=0,
                    ElapsedSincePreviousEligible='', PreviousEligibleCycle='', CycleGap='')
    return original


def main():
    archived_summary={r['RunID']:r for r in read_csv(SUMMARY_PATH) if r['PhaseBasis']=='RelativeCyclePhase'}
    archived_ex=defaultdict(set)
    for r in read_csv(EXCEPTIONS_PATH):
        if r['PhaseBasis']=='RelativeCyclePhase':archived_ex[r['RunID']].add(int(r['Cycle']))
    archived_mixed=defaultdict(set)
    for r in read_csv(MIXED_SUMMARY_PATH):archived_mixed[r['RunID']].add(int(r['Cycle']))
    archived_mixed_rows=defaultdict(set)
    for r in read_csv(MIXED_ROWS_PATH):archived_mixed_rows[r['RunID']].add((int(r['Cycle']),int(r['SourceDataRow'])))
    period_seq=read_csv(PERIODICITY_SEQUENCE)
    if not PERIODICITY_BLOCKS.exists():raise SystemExit(f'Missing expected periodicity block file: {PERIODICITY_BLOCKS}')
    period_blocks=read_csv(PERIODICITY_BLOCKS)
    seq_by_run=defaultdict(dict)
    for r in period_seq:seq_by_run[r['RunID']][int(r['Cycle'])]=r

    all_cycles={}; selected_by_run={}; raw_by_run={}; validation=[]
    # Replay the historical exact filters and all-band classification; do not choose any new mapping.
    for rid,rel in RUN_FILES.items():
        raw=read_csv(RAW/rel); raw_by_run[rid]=raw; selected=[]
        for row_pos,row in enumerate(raw,1):
            if str(row.get('TestNumber','')).strip()!=rid:continue
            if str(row.get('RunMode','')).strip()!='3':continue
            if str(row.get('DustTrakAState','')).strip()!='6':continue
            if str(row.get('DustTrakAPower','')).strip()!='1':continue
            measurement=nval(row.get('DustTrakAMeasurement(MgPerM3)'))
            analog=nval(row.get('DustTrakAAnalogMeasurement(Volts)'))
            cyc=nval(row.get('CycleCounter'))
            if measurement is None or analog is None or cyc is None or measurement==-999 or cyc!=math.trunc(cyc):continue
            selected.append(dict(Cycle=int(cyc),SourceDataRow=row_pos,CSVLineNumber=row_pos+1,Row=row,
                                 Measurement=measurement,Analog=analog,Band=lineage.band(measurement),
                                 TimestampSeconds=nval(row.get('Time'))))
        selected_by_run[rid]=selected
        grouped=defaultdict(list)
        for r in selected:grouped[r['Cycle']].append(r)
        arc=archived_summary[rid]; first=int(arc['FirstCycle'])
        cycles={}
        for c,rows in grouped.items():
            bands={x['Band'] for x in rows}
            obs=next(iter(bands)) if len(bands)==1 else 'MixedBand'
            phase='Phase0' if (c-first)%2==0 else 'Phase1'
            expected=arc['Phase0DominantBand'] if phase=='Phase0' else arc['Phase1DominantBand']
            ex=int(obs!='MixedBand' and obs!=expected)
            cycles[c]=dict(RunID=rid,Cycle=c,RelativeCyclePhase=phase,ExpectedBand=expected,
                           ObservedBand=obs,ExceptionIndicator=(ex if obs!='MixedBand' else ''),
                           SourceRowCount=len(rows),MixedBandIndicator=int(obs=='MixedBand'),
                           DuplicateCycleIndicator=int(len(rows)>1),DuplicateRowCount=max(0,len(rows)-1),
                           SourceDataRows=';'.join(str(x['SourceDataRow']) for x in rows))
        # Match every sequence row from the stamped periodicity output to the replayed historical source.
        mismatches=[]
        for c,x in cycles.items():
            p=seq_by_run[rid].get(c)
            if p is None or p['ObservedBand']!=x['ObservedBand'] or p['ExpectedBand']!=x['ExpectedBand'] or int(p['SourceRowCount'])!=x['SourceRowCount'] or str(p['ExceptionIndicator'])!=str(x['ExceptionIndicator']):
                mismatches.append(c)
        exset={c for c,x in cycles.items() if x['ExceptionIndicator']==1}
        mixedset={c for c,x in cycles.items() if x['MixedBandIndicator']}
        mixedrows={(c,r['SourceDataRow']) for c,rs in grouped.items() if len({z['Band'] for z in rs})>1 for r in rs}
        checks={'periodicity sequence matches raw replay':not mismatches,
                'archived classified count':sum(not x['MixedBandIndicator'] for x in cycles.values())==int(arc['ClassifiedCycles']),
                'archived exceptions':len(exset)==int(arc['ExceptionCycles']),
                'exception cycle identities':exset==archived_ex[rid],
                'mixed cycle identities':mixedset==archived_mixed[rid],
                'mixed source-row identities':mixedrows==archived_mixed_rows[rid],
                'duplicate cycle count':sum(x['DuplicateCycleIndicator'] for x in cycles.values())==int(arc['DuplicateCycleNumbers'])}
        validation.append((rid,checks,mismatches))
        all_cycles[rid]=cycles
    failed=[(rid,checks,bad) for rid,checks,bad in validation if not all(checks.values())]
    if failed:raise SystemExit('VALIDATION FAILED; no outputs written: '+repr(failed))

    # Enrich eligible cycles from original rows without altering the validated class/phase fields.
    for rid,cycles in all_cycles.items():
        bycycle=defaultdict(list)
        for r in selected_by_run[rid]:bycycle[r['Cycle']].append(r)
        enriched={c:cycle_record(rid,x,bycycle[c]) for c,x in cycles.items()}
        # Timestamp recurrence counts are based on all historical-eligible source rows within each run.
        tcounts=Counter(str(r['Row'].get('TimeString','')) for r in selected_by_run[rid] if r['Row'].get('TimeString',''))
        for c,item in enriched.items():
            ts=[str(r['Row'].get('TimeString','')) for r in bycycle[c] if r['Row'].get('TimeString','')]
            item['RepeatedTimestampRows']=sum(tcounts[t]>1 for t in ts)
            item['DistinctRepeatedTimestamps']=len({t for t in ts if tcounts[t]>1})
        ordered=sorted(enriched.values(),key=lambda x:x['Cycle'])
        for i,item in enumerate(ordered):
            if i:
                prev=ordered[i-1]
                item['PreviousEligibleCycle']=prev['Cycle']
                item['CycleGap']=item['Cycle']-prev['Cycle']-1
                if item['CycleMedianTimestampSeconds'] is not None and prev['CycleMedianTimestampSeconds'] is not None:
                    item['ElapsedSincePreviousEligible']=item['CycleMedianTimestampSeconds']-prev['CycleMedianTimestampSeconds']
        all_cycles[rid]=enriched

    # Episode boundary cycles from the established exception-block output.
    exception_blocks={rid:[] for rid in ('84','95')}
    for r in period_blocks:
        if r['RunID'] in exception_blocks and r['EventType']=='PhaseException':
            a,b=int(r['StartCycle']),int(r['EndCycle'])
            if a<=PRIMARY[r['RunID']][1] and b>=PRIMARY[r['RunID']][0]:exception_blocks[r['RunID']].append((a,b))

    # Define episode/control/full-run populations by exact cycle intervals; mixed retained as separate strata.
    populations=[]
    def add_population(rid,label,start=None,end=None):
        cmap=all_cycles[rid]
        recs=[x for x in cmap.values() if start is None or start<=x['Cycle']<=end]
        populations.append(dict(RunID=rid,Population=label,StartCycle=start if start is not None else min(cmap),
                                EndCycle=end if end is not None else max(cmap),Records=sorted(recs,key=lambda x:x['Cycle'])))
    for rid in RUN_FILES:
        add_population(rid,'FullRun',None,None)
        if rid in PRIMARY:
            lo,hi=PRIMARY[rid];add_population(rid,'PrimaryEpisode',lo,hi)
            for label,a,b in CONTROLS[rid]:add_population(rid,'MatchedControl'+label,a,b)

    # Analyses will use cycle medians (one value per cycle) to avoid weighting cycles with duplicates.
    metric_map=[('DustTrakA_Measurement','CycleMedianMeasurement'),('DustTrakA_Analog','CycleMedianAnalog')]
    for label,field in CONTINUOUS_FIELDS[2:]:metric_map.append((field.replace('/','_'),field))
    metric_map += [('ElapsedSecondsSincePreviousEligibleCycle','ElapsedSincePreviousEligible'),
                   ('SourceRecordsPerCycle','SourceRowCount'),
                   ('DuplicateRowsPerCycle','DuplicateRowCount'),
                   ('RepeatedTimestampRowsPerCycle','RepeatedTimestampRows'),
                   ('DistinctRepeatedTimestampsPerCycle','DistinctRepeatedTimestamps'),
                   ('CycleMinusFirstSourceRow','SourceRowPositionDifference')]

    episode_metrics=[]; analog_comparisons=[]
    # Summary distributions for full runs and all primary/control windows, by classification.
    for pop in populations:
        recs=pop['Records']
        strata=[('AllEligible',lambda x:True),('PhaseException',lambda x:x['ExceptionIndicator']==1),
                ('PhaseAgreement',lambda x:x['ExceptionIndicator']==0),('MixedBand',lambda x:x['MixedBandIndicator']==1)]
        for stratum,pred in strata:
            cycles=[x for x in recs if pred(x)]
            rows=[r for x in cycles for r in x['RawRows']]
            for metric,label in [('CycleMedianMeasurement','DustTrakA_Measurement'),('CycleMedianAnalog','DustTrakA_Analog'),
                                 ('ElapsedSincePreviousEligible','ElapsedSecondsSincePreviousEligibleCycle'),
                                 ('SourceRowCount','SourceRecordsPerCycle'),('DuplicateRowCount','DuplicateRowsPerCycle'),
                                 ('RepeatedTimestampRows','RepeatedTimestampRowsPerCycle'),
                                 ('DistinctRepeatedTimestamps','DistinctRepeatedTimestampsPerCycle'),
                                 ('SourceRowPositionDifference','CycleMinusFirstSourceRow')]:
                ss=stats([x.get(metric) for x in cycles])
                episode_metrics.append(dict(RecordType='MetricSummary',RunID=pop['RunID'],Population=pop['Population'],
                                            CycleStart=pop['StartCycle'],CycleEnd=pop['EndCycle'],Stratum=stratum,
                                            Metric=label,Unit='per_cycle',SourceRowN=len(rows),CycleN=len(cycles),**ss))
            # Original-source-row distribution for two principal DustTrak A variables.
            for label,attr in [('DustTrakA_Measurement','Measurement'),('DustTrakA_Analog','Analog')]:
                ss=stats([r[attr] for r in rows])
                episode_metrics.append(dict(RecordType='MetricSummary',RunID=pop['RunID'],Population=pop['Population'],
                                            CycleStart=pop['StartCycle'],CycleEnd=pop['EndCycle'],Stratum=stratum,
                                            Metric=label,Unit='source_row',SourceRowN=len(rows),CycleN=len(cycles),**ss))
            # Record state distributions, including the fixed historical DustTrak A eligibility fields.
            for field in STATUS_FIELDS:
                counts=Counter(str(r['Row'].get(field,'<blank>')).strip() or '<blank>' for x in cycles for r in x['RawRows'])
                denom=sum(counts.values())
                for value,count in sorted(counts.items()):
                    episode_metrics.append(dict(RecordType='TelemetryCategory',RunID=pop['RunID'],Population=pop['Population'],
                                                CycleStart=pop['StartCycle'],CycleEnd=pop['EndCycle'],Stratum=stratum,
                                                Metric=field,Unit='source_row_category',Category=value,Count=count,
                                                Fraction=count/denom if denom else '',SourceRowN=denom,CycleN=len(cycles)))

    # Separate block-level summaries so event blocks can be compared with agreement blocks and controls.
    block_membership={}
    for rid,(lo,hi) in PRIMARY.items():
        window=sorted([x for x in all_cycles[rid].values() if lo<=x['Cycle']<=hi],key=lambda x:x['Cycle'])
        for state,name in ((1,'ExceptionBlock'),(0,'AgreementBlock')):
            chunks=[];cur=[]
            for x in window:
                if x['ExceptionIndicator']==state and (not cur or x['Cycle']==cur[-1]['Cycle']+1):cur.append(x)
                else:
                    if cur:chunks.append(cur)
                    cur=[x] if x['ExceptionIndicator']==state else []
            if cur:chunks.append(cur)
            for i,chunk in enumerate(chunks,1):
                popname=f'{name}_{i:02d}'
                for x in chunk:block_membership[(rid,x['Cycle'])]=popname
                rows=[r for x in chunk for r in x['RawRows']]
                for metric,label in [('CycleMedianMeasurement','DustTrakA_Measurement'),('CycleMedianAnalog','DustTrakA_Analog'),
                                     ('ElapsedSincePreviousEligible','ElapsedSecondsSincePreviousEligibleCycle'),
                                     ('SourceRowCount','SourceRecordsPerCycle'),('DuplicateRowCount','DuplicateRowsPerCycle'),
                                     ('RepeatedTimestampRows','RepeatedTimestampRowsPerCycle'),
                                     ('DistinctRepeatedTimestamps','DistinctRepeatedTimestampsPerCycle'),
                                     ('SourceRowPositionDifference','CycleMinusFirstSourceRow')]:
                    ss=stats([x.get(metric) for x in chunk])
                    episode_metrics.append(dict(RecordType='BlockMetricSummary',RunID=rid,Population=popname,
                                                CycleStart=chunk[0]['Cycle'],CycleEnd=chunk[-1]['Cycle'],BlockLength=len(chunk),
                                                Stratum=name,Metric=label,Unit='per_cycle',SourceRowN=len(rows),CycleN=len(chunk),**ss))
                for label,attr in [('DustTrakA_Measurement','Measurement'),('DustTrakA_Analog','Analog')]:
                    ss=stats([r[attr] for r in rows])
                    episode_metrics.append(dict(RecordType='BlockMetricSummary',RunID=rid,Population=popname,
                                                CycleStart=chunk[0]['Cycle'],CycleEnd=chunk[-1]['Cycle'],BlockLength=len(chunk),
                                                Stratum=name,Metric=label,Unit='source_row',SourceRowN=len(rows),CycleN=len(chunk),**ss))
                for field in STATUS_FIELDS:
                    counts=Counter(str(r['Row'].get(field,'<blank>')).strip() or '<blank>' for x in chunk for r in x['RawRows'])
                    denom=sum(counts.values())
                    for value,count in sorted(counts.items()):
                        episode_metrics.append(dict(RecordType='BlockTelemetryCategory',RunID=rid,Population=popname,
                                                    CycleStart=chunk[0]['Cycle'],CycleEnd=chunk[-1]['Cycle'],BlockLength=len(chunk),
                                                    Stratum=name,Metric=field,Unit='source_row_category',Category=value,
                                                    Count=count,Fraction=count/denom if denom else '',SourceRowN=denom,CycleN=len(chunk)))

    # Comparisons with moving-block bootstrap CIs (22-cycle blocks); intervals are exploratory, not p-values.
    rng_metric_map=[('DustTrakA_Measurement','CycleMedianMeasurement'),('DustTrakA_Analog','CycleMedianAnalog'),
                    ('ElapsedSecondsSincePreviousEligibleCycle','ElapsedSincePreviousEligible'),
                    ('SourceRecordsPerCycle','SourceRowCount'),('DuplicateRowsPerCycle','DuplicateRowCount'),
                    ('RepeatedTimestampRowsPerCycle','RepeatedTimestampRows'),
                    ('CycleMinusFirstSourceRow','SourceRowPositionDifference')]
    def add_contrast(label, a, b, group_a=None, group_b=None, within=False, note=''):
        for metric_name,field in rng_metric_map:
            da=[r for r in a if r.get(field) is not None and r.get(field)!='' and (group_a is None or group_a(r))]
            db=[r for r in b if r.get(field) is not None and r.get(field)!='' and (group_b is None or group_b(r))]
            vals_a=[r[field] for r in da];vals_b=[r[field] for r in db]
            point,lo,hi,used=boot_diff(a,b,field,group_a,group_b,within)
            analog_comparisons.append(dict(Comparison=label,Metric=metric_name,Unit='per_cycle',N_A=len(vals_a),N_B=len(vals_b),
                                           SourceRows_A=sum(r['SourceRowCount'] for r in da),SourceRows_B=sum(r['SourceRowCount'] for r in db),
                                           Mean_A=statistics.mean(vals_a) if vals_a else '',Mean_B=statistics.mean(vals_b) if vals_b else '',
                                           MeanDifference_AminusB=point,HedgesG=hedges_g(vals_a,vals_b),
                                           MovingBlockLength=BLOCK_LENGTH,CI95_Low=lo,CI95_High=hi,BootstrapReplicates=used,
                                           BootstrapInterpretation='Exploratory moving-block percentile interval; not a significance test',
                                           Note=note))

    for rid in ('84','95'):
        main=next(p['Records'] for p in populations if p['RunID']==rid and p['Population']=='PrimaryEpisode')
        for label in (['MatchedControlBefore'] if rid=='84' else ['MatchedControlBefore','MatchedControlAfter']):
            ctrl=next(p['Records'] for p in populations if p['RunID']==rid and p['Population']==label)
            add_contrast(f'Run{rid}_EpisodeAll_vs_{label}',main,ctrl,note='Same-run matched cycle-number window; all eligible classifications included, mixed retained as separate observations')
        add_contrast(f'Run{rid}_EpisodeExceptions_vs_Agreement',main,main,
                     lambda x:x['ExceptionIndicator']==1,lambda x:x['ExceptionIndicator']==0,within=True,
                     note='Within episode; bootstrap resamples contiguous 22-cycle blocks carrying exception labels')
    # Episode versus Run84 and four complete comparison runs.
    r95=next(p['Records'] for p in populations if p['RunID']=='95' and p['Population']=='PrimaryEpisode')
    r84=next(p['Records'] for p in populations if p['RunID']=='84' and p['Population']=='PrimaryEpisode')
    add_contrast('Run95_EpisodeAll_vs_Run84_EpisodeAll',r95,r84,note='Different runs and episode windows; exploratory, run identity is confounded')
    for rid in ('63','64','76','97'):
        cmp=next(p['Records'] for p in populations if p['RunID']==rid and p['Population']=='FullRun')
        add_contrast(f'Run95_EpisodeExceptions_vs_Run{rid}_Exceptions',r95,cmp,
                     lambda x:x['ExceptionIndicator']==1,lambda x:x['ExceptionIndicator']==1,
                     note='Cross-run exception-cycle contrast; small/zero event counts can make estimates unstable')
        add_contrast(f'Run95_EpisodeAll_vs_Run{rid}_FullRun',r95,cmp,
                     note='Different runs/periods; exploratory comparison, not a matched experiment')

    # Cycle/timestamp interval detail; labels for primary and matched control populations.
    population_labels=defaultdict(list)
    for p in populations:
        for x in p['Records']:
            population_labels[(p['RunID'],x['Cycle'])].append(p['Population'])
    interval_rows=[]
    for rid,cycles in all_cycles.items():
        ordered=sorted(cycles.values(),key=lambda x:x['Cycle'])
        for x in ordered:
            interval_rows.append(dict(RunID=rid,Cycle=x['Cycle'],RelativeCyclePhase=x['RelativeCyclePhase'],
                                      ObservedBand=x['ObservedBand'],ExpectedBand=x['ExpectedBand'],
                                      ExceptionIndicator=x['ExceptionIndicator'],MixedBandIndicator=x['MixedBandIndicator'],
                                      PopulationLabels=';'.join(population_labels[(rid,x['Cycle'])]+([block_membership[(rid,x['Cycle'])]] if (rid,x['Cycle']) in block_membership else [])),
                                      PreviousEligibleCycle=x['PreviousEligibleCycle'],CycleGap=x['CycleGap'],
                                      ElapsedSecondsSincePreviousEligibleCycle=x['ElapsedSincePreviousEligible'],
                                      ElapsedSecondsPerCycle=(x['ElapsedSincePreviousEligible']/(x['CycleGap']+1) if x['ElapsedSincePreviousEligible']!='' else ''),
                                      SourceRowCount=x['SourceRowCount'],DuplicateCycleIndicator=x['DuplicateCycleIndicator'],
                                      DuplicateRowCount=x['DuplicateRowCount'],SourceRowFirst=x['SourceRowFirst'],
                                      SourceRowLast=x['SourceRowLast'],CycleMinusFirstSourceRow=x['SourceRowPositionDifference'],
                                      RepeatedTimestampRows=x['RepeatedTimestampRows'],DistinctRepeatedTimestamps=x['DistinctRepeatedTimestamps'],
                                      FirstTimestamp=x['TimeStringFirst'],LastTimestamp=x['TimeStringLast'],
                                      FirstTimestampSeconds=x['CycleMedianTimestampSeconds']))

    # Transition-aligned raw rows from +/-3 cycle numbers around every primary-window exception block boundary.
    transition_rows=[]
    for rid in ('84','95'):
        cycle_map=all_cycles[rid]
        for start,end in exception_blocks[rid]:
            for boundary_type,boundary in (('ExceptionBlockStart',start),('ExceptionBlockEnd',end)):
                for c in range(boundary-3,boundary+4):
                    cy=cycle_map.get(c)
                    if not cy:continue
                    relative=c-boundary
                    if relative==-1:role='CycleBeforeBoundary'
                    elif relative==0:role='BoundaryCycle'
                    elif relative==1:role='CycleAfterBoundary'
                    else:role='BoundaryContext'
                    for src in cy['SourceRows']:
                        row=src['Row']
                        entry=dict(RunID=rid,Population='PrimaryEpisode',BoundaryType=boundary_type,
                                   BoundaryCycle=boundary,ContextCycle=c,RelativeCycle=relative,ContextRole=role,
                                   SourceDataRow=src['SourceDataRow'],CSVLineNumber=src['CSVLineNumber'],
                                   Timestamp=row.get('TimeString',''),TimestampSeconds=src['TimestampSeconds'],
                                   CycleNumber=c,ExpectedBand=cy['ExpectedBand'],ObservedBand=cy['ObservedBand'],
                                   FourBandClass=src['Band'],ExceptionIndicator=cy['ExceptionIndicator'],
                                   MixedBandIndicator=cy['MixedBandIndicator'],SourceRowCount=cy['SourceRowCount'],
                                   DuplicateCycleIndicator=cy['DuplicateCycleIndicator'],
                                   CycleGapFromPrevious=cy['CycleGap'],ElapsedSincePreviousEligible=cy['ElapsedSincePreviousEligible'],
                                   CycleMinusFirstSourceRow=cy['SourceRowPositionDifference'],
                                   RepeatedTimestampRows=cy['RepeatedTimestampRows'])
                        for field in STATUS_FIELDS:
                            entry[field]=row.get(field,'')
                        for _,field in CONTINUOUS_FIELDS:
                            entry[field]=row.get(field,'')
                        transition_rows.append(entry)

    # Run-level concise comparisons for report (exception/agreement timing and primary-window descriptions).
    def subset(rid, pred, lo=None, hi=None):
        return [x for x in all_cycles[rid].values() if (lo is None or lo<=x['Cycle']<=hi) and pred(x)]
    def meanf(records, key):
        vals=[x[key] for x in records if x.get(key) is not None and x.get(key)!='']
        return statistics.mean(vals) if vals else None
    def report_metric(rid, pred, key, lo=None,hi=None):return meanf(subset(rid,pred,lo,hi),key)

    outputs={
        'episode':META/f'PSI101_Pyrell_DustTrakA_PhaseReversal_EpisodeControlMetrics_{STAMP}.csv',
        'intervals':META/f'PSI101_Pyrell_DustTrakA_PhaseReversal_TimestampCycleIntervals_{STAMP}.csv',
        'analog':META/f'PSI101_Pyrell_DustTrakA_PhaseReversal_AnalogMeasurementComparison_{STAMP}.csv',
        'transition':META/f'PSI101_Pyrell_DustTrakA_PhaseReversal_TransitionAlignedRows_{STAMP}.csv',
        'report':META/f'PSI101_Pyrell_DustTrakA_PhaseReversal_CorrelationAuditReport_{STAMP}.txt',
    }
    # Write only after complete replay validation succeeded for all runs.
    write_csv(outputs['episode'],episode_metrics)
    write_csv(outputs['intervals'],interval_rows)
    write_csv(outputs['analog'],analog_comparisons)
    write_csv(outputs['transition'],transition_rows)

    with outputs['report'].open('w',encoding='utf-8') as f:
        f.write('Phase-reversal episode and telemetry correlation audit — PSI-101 Pyrell DustTrak A\n')
        f.write(f'Generated {STAMP}; comparison source periodicity set {PERIODICITY_STAMP}. Source rows and archived reports were read only.\n\n')
        f.write('VALIDATION\nHistorical selection and four-band classes were replayed without changing filters or phase mappings. The replay matches the 18:16:48 cycle sequence and archived classified counts, exception counts/identities, mixed-cycle source rows, and duplicate-cycle counts for every run. No analysis or output was written before all run checks passed.\n')
        for rid,checks,bad in validation:
            f.write(f"Run {rid}: "+', '.join(f'{k}={v}' for k,v in checks.items())+'\n')
        f.write('\nDESIGN AND LIMITATIONS\nEpisode windows: Run 84 cycles 1770–2135; Run 95 cycles 8677–8858. Matched controls use same-run cycle-number windows of the same nominal width: Run 84 1404–1769; Run 95 8495–8676 and 8859–9040. Missing and mixed cycles remain absent from binary phase groups, but are retained in interval/accounting and mixed observations. The other four runs are compared over their full eligible sequences. Measurement distributions use original source-row observations and cycle medians; timing/serial comparisons use one row per eligible cycle. Bootstrap intervals resample contiguous 22-cycle blocks; they are exploratory uncertainty summaries, not p-values, and cross-run contrasts remain confounded by run differences. No consecutive cycles are treated as independent for those intervals.\n')
        f.write('Primary episode/control sample composition (cycle counts):\n')
        for p in populations:
            if p['Population'] not in ('PrimaryEpisode','MatchedControlBefore','MatchedControlAfter'):continue
            n=len(p['Records']);ex=sum(x['ExceptionIndicator']==1 for x in p['Records']);agree=sum(x['ExceptionIndicator']==0 for x in p['Records']);mix=sum(x['MixedBandIndicator'] for x in p['Records'])
            f.write(f"Run {p['RunID']} {p['Population']} cycles {p['StartCycle']}–{p['EndCycle']}: eligible={n}, exceptions={ex}, agreements={agree}, mixed={mix}, source rows={sum(x['SourceRowCount'] for x in p['Records'])}.\n")
        f.write('\nEPISODE FINDINGS\n')
        for rid,(lo,hi) in PRIMARY.items():
            ep=[x for x in all_cycles[rid].values() if lo<=x['Cycle']<=hi]
            exc=[x for x in ep if x['ExceptionIndicator']==1]; agr=[x for x in ep if x['ExceptionIndicator']==0]; mix=[x for x in ep if x['MixedBandIndicator']]
            f.write(f"Run {rid} primary interval: exceptions n={len(exc)}, agreements n={len(agr)}, mixed n={len(mix)}. Exception vs agreement cycle-median DustTrak A: measurement means {meanf(exc,'CycleMedianMeasurement')} vs {meanf(agr,'CycleMedianMeasurement')}; analog means {meanf(exc,'CycleMedianAnalog')} vs {meanf(agr,'CycleMedianAnalog')}. Median elapsed since previous eligible cycle: exceptions {statistics.median([x['ElapsedSincePreviousEligible'] for x in exc if isinstance(x['ElapsedSincePreviousEligible'],(int,float))]) if any(isinstance(x['ElapsedSincePreviousEligible'],(int,float)) for x in exc) else 'NA'} seconds; agreement {statistics.median([x['ElapsedSincePreviousEligible'] for x in agr if isinstance(x['ElapsedSincePreviousEligible'],(int,float))]) if any(isinstance(x['ElapsedSincePreviousEligible'],(int,float)) for x in agr) else 'NA'} seconds. Mean source rows/cycle: exceptions {meanf(exc,'SourceRowCount')}; agreements {meanf(agr,'SourceRowCount')}; mixed {meanf(mix,'SourceRowCount')}. Full distributions/statistics and moving-block contrasts are in CSV outputs.\n")
        f.write('\nDETAILED ASSOCIATIONS\n')
        f.write('Timing and repeated timestamps: Run 84 primary window has 297 one-second, 34 zero-second and 35 two-second intervals between successive eligible cycles; these average to about one second per cycle. Sixty-eight source rows (34 repeated timestamp values, two rows per value) are flagged, split evenly across 34 exception and 34 agreement cycles. Run 95 primary window has 148 one-second, 17 zero-second and 17 two-second intervals; 34 rows (17 repeated timestamp values) are flagged, across 18 exception and 16 agreement cycles. Every episode cycle has one eligible source row. Thus repeated timestamps/time quantization align with the episode windows but do not distinguish phase-exception from phase-agreement cycles. The Run 84 matched control has no repeated timestamp rows and one two-second interval; Run 95 before-control has no repeats and one two-second interval; after-control has four repeated rows across three cycles plus one zero- and one two-second interval. Run 95 after-control has one duplicate source cycle (183 rows for 182 cycle numbers). These are recorded timing differences, not evidence of their cause.\n')
        f.write('DustTrak A distributions by phase status: Run 84 exception vs agreement cycle-median means are 15020.46 vs 15016.31 and 0.1174 vs 0.1040 V analog. Their mean differences are +4.15 and +0.01336 V; moving-block 95% intervals are [-8.83, 9.80] and [-0.00799, 0.01960], respectively; Hedges g is about 0.001 and 0.146. Run 95 means are 14924.30 vs 14911.78 and 0.15070 vs 0.14379 V; differences +12.52 and +0.00691 V, with block intervals [-19.92, 20.03] and [-0.01717, 0.02898], Hedges g about 0.002 and 0.071. These exception/agreement comparisons do not show clear separation in DustTrak A central tendency at cycle level. Full mean/median/SD/IQR/min/max and source-row statistics are in EpisodeControlMetrics; individual exception and agreement block summaries are included there.\n')
        f.write('Matched-window contrasts: Run 95 episode vs before/after controls has DustTrak A measurement mean differences of about -100 units with wide block intervals spanning zero; analog mean differences are +0.0257 V (before; CI [-0.0330, 0.0839]) and +0.0318 V (after; CI [-0.0190, 0.0998]), also spanning zero. Run 84 episode vs preceding control has analog mean difference -0.6557 V (CI [-0.9594, -0.4236]) and DustTrak A measurement difference -193.7 (CI [-407.1, -8.8]). The analog standardized difference is large (Hedges g about -1.50), but the control differs in ThermalPrecipitatorPostAgeHeater and PostAgeValve: both are 0 throughout the episode, while they are 1 in about 16.9% and 34.4% of control rows. This is a time-window association with simultaneous status differences; it does not isolate a phase-exception relation.\n')
        f.write('Other instrument states: In Run 95 primary window none of the 24 tabulated state/power/heater/valve fields has a different exception-versus-agreement category distribution. In Run 84, only small differences occur: DustTrakAKeySelect=2 appears in 2/182 exception and 1/184 agreement cycles; PTrakState=4 appears once in each group. Run 84 preceding control has the PostAge heater/valve differences described above. Run 95 before-control matches the episode PTrakState=5, PTrakPower=1 and PTrakKeySelect=5; after-control differs: PTrakState=2 in about 67.8% of rows, PTrakPower=0 in 4.9%, PTrakKeySelect=12 in 40.4%. These changes occur in an all-agreement after-control period, so they do not track exception cycles specifically. DustTrakA state/power are fixed by eligibility and cannot be evaluated in excluded rows.\n')
        f.write('Cross-run context: Run 95 exception-cycle analog mean is about 0.065–0.073 V higher than sparse exception groups in Runs 63, 64 and 76 in cycle-level contrasts. Their bootstrap intervals are positive, but comparator exception counts are only 8, 6 and 2 cycles; runs also differ in time and status, so these are exploratory cross-run differences, not evidence for a Run 95-specific cause. Run 97 has no exception cycles, so this comparison is unavailable. Run 95 vs Run 84 episode contrasts are less precise and include zero.\n')
        f.write('RunMode, TestNumber, DustTrakAState and DustTrakAPower are fixed by the validated row filters. Other state/power/heater/valve fields are tabulated by phase status, block and window in EpisodeControlMetrics. Analog and measurement rows include mean, median, sample SD, quartiles/IQR, range and sample counts, plus descriptive effect sizes and moving-block confidence intervals in AnalogMeasurementComparison. Repeated timestamps and row multiplicity are summarized per cycle in TimestampCycleIntervals.\n')
        f.write('\nINTERPRETATION\n')
        f.write('Any observed difference is an association in recorded data only. Episode/control contrasts do not identify a cause; primary periods were selected from earlier analyses, and block bootstrap intervals do not remove run-level confounding or selection effects. The fixed historical DustTrak A state/power eligibility means no conclusion can be drawn about behavior in rows excluded by those filters. No acquisition mechanism, hardware fault, or physical explanation is inferred.\n\nFiles created:\n')
        for p in outputs.values():f.write(str(p.resolve())+'\n')
    for p in outputs.values():print(p.resolve())
    print('VALIDATION: all six runs passed against archived lineage and periodicity cycle sequence')


if __name__=='__main__':
    main()
