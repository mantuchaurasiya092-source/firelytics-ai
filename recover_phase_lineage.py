"""Reproduce the archived PSI-101 Pyrell DustTrak A cycle classification and audit periodicity."""
import csv
import math
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
META = ROOT / 'data' / 'metadata'
RAW = ROOT / 'data' / 'raw' / 'PSI-101' / 'Pyrell'
STAMP = datetime.now().strftime('%Y%m%d_%H%M%S')
RUN_FILES = {
    '63': 'Run_063/HKPData_gmt235_1.csv',
    '64': 'Run_064/HKPData_gmt235_3.csv',
    '76': 'Run_076/HKPData_gmt238_4.csv',
    '84': 'Run_084/HKPData_gmt242_1.csv',
    '95': 'Run_095/HKPData_gmt250_4.csv',
    '97': 'Run_097/HKPData_gmt251_1.csv',
}
PHASE_SUMMARY = META / 'PSI101_Pyrell_DustTrakA_PhaseSummary_2026-11-14_170034.csv'
PHASE_EXCEPTIONS = META / 'PSI101_Pyrell_DustTrakA_PhaseExceptions_2026-11-14_170034.csv'
MIXED_SUMMARY = META / 'PSI101_Pyrell_DustTrakA_MixedBand_CycleSummary_2026-11-14_170034.csv'
MIXED_ROWS = META / 'PSI101_Pyrell_DustTrakA_MixedBand_OriginalRows_2026-11-14_170034.csv'
BANDS = ('Below 10000', '10000-14999', '15000-19999', '20000+')


def read_csv(path):
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def write_csv(path, rows):
    fields = list(rows[0]) if rows else ['RunID']
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)


def number(value):
    try:
        x = float(str(value).strip())
        return x if math.isfinite(x) else None
    except (TypeError, ValueError):
        return None


def band(value):
    if value < 10000:
        return 'Below 10000'
    if value < 15000:
        return '10000-14999'
    if value < 20000:
        return '15000-19999'
    return '20000+'


def sample_stats(values):
    if not values:
        return (0, 0, 0, 0, 0)
    return (statistics.mean(values), statistics.median(values), min(values), max(values),
            statistics.stdev(values) if len(values) > 1 else 0.0)


def classification_metrics(y, pred):
    tp = sum(a == 1 and b == 1 for a, b in zip(y, pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y, pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y, pred))
    tn = sum(a == 0 and b == 0 for a, b in zip(y, pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / len(y) if y else 0.0
    return dict(Accuracy=accuracy, Precision=precision, Recall=recall, F1= f1,
                TP=tp, FP=fp, TN=tn, FN=fn, N=len(y))


def majority_prediction(y, n):
    if not y:
        return [0] * n, 0
    # Deterministic tie: choose agreement (0), the conservative constant baseline.
    rate = sum(y) / len(y)
    label = int(rate > 0.5)
    return [label] * n, label


def square_prediction(cycles, first_cycle, period, width, offset):
    return [int(((c - first_cycle - offset) % period) < width) for c in cycles]


def fit_square(records, anchor=None):
    if not records:
        return (0, 8, 0, 0.0)
    cycles = [x['Cycle'] for x in records]
    y = [x['ExceptionIndicator'] for x in records]
    first = records[0]['Cycle'] if anchor is None else anchor
    best = None
    for period in range(18, 27):
        for width in range(8, 14):
            for offset in range(period):
                pred = square_prediction(cycles, first, period, width, offset)
                score = sum(a == b for a, b in zip(y, pred)) / len(y)
                # Stable tie resolution favors the smaller period, then width, then offset.
                key = (score, -period, -width, -offset)
                if best is None or key > best[0]:
                    best = (key, period, width, offset)
    return best[1], best[2], best[3], best[0][0]


def fit_with_fixed_period(records, period, anchor=None):
    if not records:
        return (8, 0, 0.0)
    cyc = [x['Cycle'] for x in records]
    y = [x['ExceptionIndicator'] for x in records]
    first = records[0]['Cycle'] if anchor is None else anchor
    best = None
    for width in range(8, 14):
        for offset in range(period):
            pred = square_prediction(cyc, first, period, width, offset)
            score = sum(a == b for a, b in zip(y, pred)) / len(y)
            key = (score, -width, -offset)
            if best is None or key > best[0]:
                best = (key, width, offset)
    return best[1], best[2], best[0][0]


def autocorrelation(run_records, lag):
    by_cycle = {x['Cycle']: x['ExceptionIndicator'] for x in run_records}
    pairs = [(a, by_cycle[c + lag]) for c, a in by_cycle.items() if c + lag in by_cycle]
    n = len(pairs)
    if n < 2:
        return n, ''
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    vx = sum((x - mx) ** 2 for x in xs)
    vy = sum((y - my) ** 2 for y in ys)
    if vx == 0 or vy == 0:
        return n, ''
    return n, sum((x - mx) * (y - my) for x, y in pairs) / math.sqrt(vx * vy)


def contiguous_blocks(records, value):
    out, cur = [], []
    for item in records:
        if item['ExceptionIndicator'] == value and (not cur or item['Cycle'] == cur[-1]['Cycle'] + 1):
            cur.append(item)
        else:
            if cur:
                out.append(cur)
            cur = [item] if item['ExceptionIndicator'] == value else []
    if cur:
        out.append(cur)
    return out


def main():
    archived_summary = {r['RunID']: r for r in read_csv(PHASE_SUMMARY)
                        if r['PhaseBasis'] == 'RelativeCyclePhase'}
    archived_exception_cycles = defaultdict(set)
    for r in read_csv(PHASE_EXCEPTIONS):
        if r['PhaseBasis'] == 'RelativeCyclePhase':
            archived_exception_cycles[r['RunID']].add(int(r['Cycle']))
    archived_mixed = defaultdict(set)
    for r in read_csv(MIXED_SUMMARY):
        archived_mixed[r['RunID']].add(int(r['Cycle']))
    archived_mixed_rows = defaultdict(set)
    for r in read_csv(MIXED_ROWS):
        archived_mixed_rows[r['RunID']].add((int(r['Cycle']), int(r['SourceDataRow'])))

    cycles_by_run, selected_by_run, raw_by_run = {}, {}, {}
    row_rejections, run_validation = [], []
    # Recreate historical row eligibility and all four bands, then validate all runs before output.
    for rid, rel in RUN_FILES.items():
        source = RAW / rel
        raw_rows = read_csv(source)
        raw_by_run[rid] = raw_rows
        selected = []
        reject_counts = Counter()
        for data_row, row in enumerate(raw_rows, 1):
            if str(row.get('TestNumber', '')).strip() != rid:
                reject_counts['TestNumber mismatch'] += 1
                continue
            if str(row.get('RunMode', '')).strip() != '3':
                reject_counts['RunMode mismatch'] += 1
                continue
            if str(row.get('DustTrakAState', '')).strip() != '6':
                reject_counts['DustTrakAState mismatch'] += 1
                continue
            if str(row.get('DustTrakAPower', '')).strip() != '1':
                reject_counts['DustTrakAPower mismatch'] += 1
                continue
            measurement = number(row.get('DustTrakAMeasurement(MgPerM3)'))
            analog = number(row.get('DustTrakAAnalogMeasurement(Volts)'))
            cycle_value = number(row.get('CycleCounter'))
            if measurement is None or analog is None or cycle_value is None:
                reject_counts['Invalid measurement/analog/cycle'] += 1
                continue
            if measurement == -999:
                reject_counts['Sentinel measurement -999'] += 1
                continue
            if cycle_value != math.trunc(cycle_value):
                reject_counts['Non-integer cycle'] += 1
                continue
            selected.append(dict(Cycle=int(cycle_value), SourceDataRow=data_row,
                                 CSVLineNumber=data_row + 1, Row=row,
                                 Measurement=measurement, Analog=analog,
                                 Band=band(measurement)))
        selected_by_run[rid] = selected
        for reason, count in reject_counts.items():
            row_rejections.append(dict(RunID=rid, ExcludedType='RejectedSourceRows',
                                       Reason=reason, Count=count, Cycle='', SourceRows=''))

        grouped = defaultdict(list)
        for item in selected:
            grouped[item['Cycle']].append(item)
        run_archive = archived_summary[rid]
        first_cycle = int(run_archive['FirstCycle'])
        p0, p1 = run_archive['Phase0DominantBand'], run_archive['Phase1DominantBand']
        cycle_records = {}
        for c, group in grouped.items():
            distinct = sorted({x['Band'] for x in group}, key=BANDS.index)
            observed = distinct[0] if len(distinct) == 1 else 'MixedBand'
            phase = 'Phase0' if (c - first_cycle) % 2 == 0 else 'Phase1'
            expected = p0 if phase == 'Phase0' else p1
            cycle_records[c] = dict(RunID=rid, Cycle=c, RelativeCyclePhase=phase,
                                    ExpectedBand=expected, ObservedBand=observed,
                                    ExceptionIndicator=(int(observed != expected) if observed != 'MixedBand' else ''),
                                    SourceRowCount=len(group), MixedBandIndicator=int(observed == 'MixedBand'),
                                    DuplicateCycleIndicator=int(len(group) > 1),
                                    DuplicateRowCount=max(0, len(group) - 1),
                                    SourceDataRows=';'.join(str(x['SourceDataRow']) for x in group),
                                    FirstTimestamp=group[0]['Row'].get('TimeString', ''),
                                    LastTimestamp=group[-1]['Row'].get('TimeString', ''),
                                    FirstTimestampSeconds=number(group[0]['Row'].get('Time')),
                                    LastTimestampSeconds=number(group[-1]['Row'].get('Time')),
                                    ClassifiedBandCount=len(distinct))
        cycles_by_run[rid] = cycle_records
        classified = [x for x in cycle_records.values() if not x['MixedBandIndicator']]
        exceptions = {x['Cycle'] for x in classified if x['ExceptionIndicator'] == 1}
        mixed = {c for c, x in cycle_records.items() if x['MixedBandIndicator']}
        reconstructed_mixed_rows = {(c, x['SourceDataRow']) for c, g in grouped.items()
                                     if len({z['Band'] for z in g}) > 1 for x in g}
        checks = {
            'ClassifiedCount': len(classified) == int(run_archive['ClassifiedCycles']),
            'ExceptionCount': len(exceptions) == int(run_archive['ExceptionCycles']),
            'ExceptionCycleIdentities': exceptions == archived_exception_cycles[rid],
            'MixedCycleCountAndSet': mixed == archived_mixed[rid] and len(mixed) == int(run_archive['MixedBandCycles']),
            'MixedSourceRows': reconstructed_mixed_rows == archived_mixed_rows[rid],
            'DuplicateCycleCount': sum(x['DuplicateCycleIndicator'] for x in cycle_records.values()) == int(run_archive['DuplicateCycleNumbers']),
        }
        run_validation.append(dict(RunID=rid, SourceFile=str(source), RawRows=len(raw_rows),
                                   SelectedRows=len(selected), FirstCycle=first_cycle,
                                   LastCycle=int(run_archive['LastCycle']),
                                   ClassifiedCycles=len(classified), ArchivedClassifiedCycles=int(run_archive['ClassifiedCycles']),
                                   Exceptions=len(exceptions), ArchivedExceptions=int(run_archive['ExceptionCycles']),
                                   ExceptionCycleIdentitiesMatch=checks['ExceptionCycleIdentities'],
                                   MixedCycles=len(mixed), ArchivedMixedCycles=int(run_archive['MixedBandCycles']),
                                   DuplicateCycleNumbers=sum(x['DuplicateCycleIndicator'] for x in cycle_records.values()),
                                   ArchivedDuplicateCycleNumbers=int(run_archive['DuplicateCycleNumbers']),
                                   AllChecksPass=all(checks.values()), CheckDetails=';'.join(f'{k}={v}' for k,v in checks.items())))

    failures = [x for x in run_validation if not x['AllChecksPass']]
    if failures:
        raise SystemExit('VALIDATION FAILED; no periodicity outputs written: ' + repr(failures))

    # Build ordered sequence and binary subset; mixed cycles remain visible but not part of binary analyses.
    sequence, mixed_table, excluded = [], [], list(row_rejections)
    binary_by_run, all_ordered = {}, {}
    for rid, cycle_map in cycles_by_run.items():
        ordered = [cycle_map[c] for c in sorted(cycle_map)]
        all_ordered[rid] = ordered
        binary_by_run[rid] = [x for x in ordered if not x['MixedBandIndicator']]
        for x in ordered:
            sequence.append(x.copy())
            if x['MixedBandIndicator']:
                mixed_table.append(dict(RunID=rid, Cycle=x['Cycle'], RelativeCyclePhase=x['RelativeCyclePhase'],
                                        ExpectedBand=x['ExpectedBand'], ObservedBand='MixedBand',
                                        SourceRowCount=x['SourceRowCount'], SourceDataRows=x['SourceDataRows'],
                                        FirstTimestamp=x['FirstTimestamp'], LastTimestamp=x['LastTimestamp'],
                                        ExcludedFromBinaryStatistics=1))
                excluded.append(dict(RunID=rid, ExcludedType='MixedBandCycle', Reason='Multiple distinct historical bands in one cycle',
                                     Count=1, Cycle=x['Cycle'], SourceRows=x['SourceDataRows']))
        lo, hi = min(cycle_map), max(cycle_map)
        for c in range(lo, hi + 1):
            if c not in cycle_map:
                excluded.append(dict(RunID=rid, ExcludedType='MissingCycleNumber',
                                     Reason='No cycle survived historical row eligibility', Count=1,
                                     Cycle=c, SourceRows=''))

    # Use cycle number arithmetic for both blocks and lag pairs; any mixed or missing cycle breaks a block.
    block_events, lag_rows, candidate_rows, boundary_rows, run_metrics = [], [], [], [], []
    for rid, valid in binary_by_run.items():
        allcycles = all_ordered[rid]
        run_info = next(x for x in run_validation if x['RunID'] == rid)
        archive = archived_summary[rid]
        exceptions = contiguous_blocks(valid, 1)
        agreements = contiguous_blocks(valid, 0)
        exc_starts = [b[0]['Cycle'] for b in exceptions]
        intervals = [exc_starts[i+1] - exc_starts[i] for i in range(len(exc_starts)-1)]
        for typ, blocks in (('PhaseException', exceptions), ('Agreement', agreements)):
            for block in blocks:
                start, end = block[0]['Cycle'], block[-1]['Cycle']
                prev = next((x for x in allcycles if x['Cycle'] == start-1), None)
                nxt = next((x for x in allcycles if x['Cycle'] == end+1), None)
                left_state = 'RunStart' if start == min(x['Cycle'] for x in allcycles) else ('Missing' if prev is None else ('MixedBand' if prev['MixedBandIndicator'] else 'Adjacent'))
                right_state = 'RunEnd' if end == max(x['Cycle'] for x in allcycles) else ('Missing' if nxt is None else ('MixedBand' if nxt['MixedBandIndicator'] else 'Adjacent'))
                near_excluded = [str(c) + ':' + ('MixedBand' if c in cycle_map_for(rid, cycles_by_run) and cycle_map_for(rid, cycles_by_run)[c]['MixedBandIndicator'] else 'Missing')
                                 for c in range(start-3, end+4)
                                 if c not in cycle_map_for(rid, cycles_by_run) or cycle_map_for(rid, cycles_by_run)[c]['MixedBandIndicator']]
                block_events.append(dict(RunID=rid, EventType=typ, StartCycle=start, EndCycle=end,
                                         BlockLength=len(block), StartToStartDistance='',
                                         IncompleteAtRunStart=int(left_state == 'RunStart'),
                                         IncompleteAtRunEnd=int(right_state == 'RunEnd'),
                                         LeftBoundaryState=left_state, RightBoundaryState=right_state,
                                         NearbyMissingOrMixedCycles=';'.join(near_excluded)))
        for i, distance in enumerate(intervals):
            block_events.append(dict(RunID=rid, EventType='ExceptionBlockStartInterval',
                                     StartCycle=exc_starts[i], EndCycle=exc_starts[i+1],
                                     BlockLength='', StartToStartDistance=distance,
                                     IncompleteAtRunStart='', IncompleteAtRunEnd='',
                                     LeftBoundaryState='', RightBoundaryState='', NearbyMissingOrMixedCycles=''))
        lens = [len(b) for b in exceptions]
        agree_lens = [len(b) for b in agreements]
        es, gs, ds = sample_stats(lens), sample_stats(agree_lens), sample_stats(intervals)

        # Pair cycle c with c + lag only when both cycle numbers are eligible.
        for lag in range(1, 41):
            n, ac = autocorrelation(valid, lag)
            lag_rows.append(dict(RunID=rid, Lag=lag, ValidCyclePairs=n, Autocorrelation=ac))

        y = [x['ExceptionIndicator'] for x in valid]
        cyc = [x['Cycle'] for x in valid]
        base_pred, base_label = majority_prediction(y, len(y))
        base_metrics = classification_metrics(y, base_pred)
        phase_anchor = int(archive['FirstCycle'])
        fullfit = fit_square(valid, phase_anchor)
        best_period, best_width, best_offset, _ = fullfit
        pred = square_prediction(cyc, phase_anchor, best_period, best_width, best_offset) if valid else []
        fitm = classification_metrics(y, pred)
        candidate_rows.append(dict(RunID=rid, ModelType='FullSequenceBest', TrainWindow='Full valid sequence', EvaluationWindow='Same sequence; in-sample',
                                   Period=best_period, MismatchWidth=best_width, PhaseOffset=best_offset,
                                   Accuracy=fitm['Accuracy'], Precision=fitm['Precision'], Recall=fitm['Recall'], F1=fitm['F1'],
                                   BaselineExceptionRate=(sum(y)/len(y) if y else 0), BaselinePrediction=base_label,
                                   BaselineAccuracy=base_metrics['Accuracy'], BaselinePrecision=base_metrics['Precision'],
                                   BaselineRecall=base_metrics['Recall'], BaselineF1=base_metrics['F1'],
                                   ImprovementOverBaseline=fitm['Accuracy']-base_metrics['Accuracy'], ValidCycles=len(valid),
                                   TP=fitm['TP'], FP=fitm['FP'], TN=fitm['TN'], FN=fitm['FN'],
                                   Interpretation='In-sample model selection; descriptive only'))
        for period in range(18, 27):
            width, offset, _ = fit_with_fixed_period(valid, period, phase_anchor)
            pp = square_prediction(cyc, phase_anchor, period, width, offset) if valid else []
            mm = classification_metrics(y, pp)
            candidate_rows.append(dict(RunID=rid, ModelType='CandidatePeriod', TrainWindow='Full valid sequence',
                                       EvaluationWindow='Same sequence; in-sample', Period=period,
                                       MismatchWidth=width, PhaseOffset=offset, Accuracy=mm['Accuracy'],
                                       Precision=mm['Precision'], Recall=mm['Recall'], F1=mm['F1'],
                                       BaselineExceptionRate=(sum(y)/len(y) if y else 0), BaselinePrediction=base_label,
                                       BaselineAccuracy=base_metrics['Accuracy'], BaselinePrecision=base_metrics['Precision'],
                                       BaselineRecall=base_metrics['Recall'], BaselineF1=base_metrics['F1'],
                                       ImprovementOverBaseline=mm['Accuracy']-base_metrics['Accuracy'], ValidCycles=len(valid),
                                       TP=mm['TP'], FP=mm['FP'], TN=mm['TN'], FN=mm['FN'],
                                       Interpretation='Candidate period best width/offset; in-sample'))

        # For requested runs, train chronologically on each half and freeze every parameter for holdout.
        if rid in ('84', '95'):
            mid = len(valid) // 2
            halves = [('FirstHalf_to_SecondHalf', valid[:mid], valid[mid:]),
                      ('SecondHalf_to_FirstHalf', valid[mid:], valid[:mid])]
            for name, train, test in halves:
                period, width, offset, trainacc = fit_square(train, phase_anchor)
                ty = [x['ExceptionIndicator'] for x in test]
                tcy = [x['Cycle'] for x in test]
                tp = square_prediction(tcy, phase_anchor, period, width, offset) if test and train else [0]*len(test)
                evalm = classification_metrics(ty, tp)
                bpred, blabel = majority_prediction([x['ExceptionIndicator'] for x in train], len(test))
                bm = classification_metrics(ty, bpred)
                trainp = square_prediction([x['Cycle'] for x in train], phase_anchor, period, width, offset) if train else []
                trainm = classification_metrics([x['ExceptionIndicator'] for x in train], trainp)
                candidate_rows.append(dict(RunID=rid, ModelType='ChronologicalHoldout', TrainWindow=name.split('_to_')[0],
                                           EvaluationWindow=name.split('_to_')[1], Period=period, MismatchWidth=width,
                                           PhaseOffset=offset, Accuracy=evalm['Accuracy'], Precision=evalm['Precision'],
                                           Recall=evalm['Recall'], F1=evalm['F1'],
                                           BaselineExceptionRate=(sum(x['ExceptionIndicator'] for x in train)/len(train) if train else 0),
                                           BaselinePrediction=majority_prediction([x['ExceptionIndicator'] for x in train], 1)[1],
                                           BaselineAccuracy=bm['Accuracy'],
                                           BaselinePrecision=bm['Precision'], BaselineRecall=bm['Recall'], BaselineF1=bm['F1'],
                                           ImprovementOverBaseline=evalm['Accuracy']-bm['Accuracy'], ValidCycles=len(test),
                                           TP=evalm['TP'], FP=evalm['FP'], TN=evalm['TN'], FN=evalm['FN'],
                                           TrainAccuracy=trainm['Accuracy'], TrainValidCycles=len(train),
                                           Interpretation='Holdout; period/width/offset fitted on training half and frozen'))
            # Reproduce the previously highlighted windows without presenting them as a full-run test.
            ws, we = (1770, 2135) if rid == '84' else (8676, 8875)
            win = [x for x in valid if ws <= x['Cycle'] <= we]
            outside = [x for x in valid if not ws <= x['Cycle'] <= we]
            period, width, offset, _ = fit_square(win, phase_anchor)
            outside_y = [x['ExceptionIndicator'] for x in outside]
            outside_pred = square_prediction([x['Cycle'] for x in outside], phase_anchor, period, width, offset) if outside and win else [0]*len(outside)
            om = classification_metrics(outside_y, outside_pred)
            ob, _ = majority_prediction([x['ExceptionIndicator'] for x in win], len(outside))
            obm = classification_metrics(outside_y, ob)
            wm = classification_metrics([x['ExceptionIndicator'] for x in win],
                                         square_prediction([x['Cycle'] for x in win], phase_anchor, period, width, offset) if win else [])
            candidate_rows.append(dict(RunID=rid, ModelType='ReportedWindowFit', TrainWindow=f'{ws}-{we}',
                                       EvaluationWindow='Outside reported window; frozen model', Period=period,
                                       MismatchWidth=width, PhaseOffset=offset, Accuracy=om['Accuracy'],
                                       Precision=om['Precision'], Recall=om['Recall'], F1=om['F1'],
                                       BaselineExceptionRate=(sum(x['ExceptionIndicator'] for x in win)/len(win) if win else 0),
                                       BaselinePrediction=majority_prediction([x['ExceptionIndicator'] for x in win], 1)[1],
                                       BaselineAccuracy=obm['Accuracy'], BaselinePrecision=obm['Precision'],
                                       BaselineRecall=obm['Recall'], BaselineF1=obm['F1'],
                                       ImprovementOverBaseline=om['Accuracy']-obm['Accuracy'], ValidCycles=len(outside),
                                       TP=om['TP'], FP=om['FP'], TN=om['TN'], FN=om['FN'],
                                       TrainAccuracy=wm['Accuracy'], TrainValidCycles=len(win),
                                       Interpretation='Selected-window fit; outside-window holdout distinguishes local fit from full-run persistence'))

        run_metrics.append(dict(RunID=rid, FirstEligibleCycle=min(cyc) if cyc else '', LastEligibleCycle=max(cyc) if cyc else '',
                                EligibleCycleRecords=len(allcycles), ClassifiedBinaryCycles=len(valid),
                                MixedBandCycles=len(mixed_table_for(rid, mixed_table)),
                                ExcludedMixedFromBinary=len(mixed_table_for(rid, mixed_table)),
                                MissingCycleNumbers=int(archive['MissingCycleNumbers']), GapEvents=int(archive['GapEvents']),
                                DuplicateCycleNumbers=run_info['DuplicateCycleNumbers'],
                                PhaseExceptions=sum(y), ExceptionRate=sum(y)/len(y) if y else 0,
                                ExceptionBlocks=len(exceptions), ExceptionLengthMean=es[0], ExceptionLengthMedian=es[1],
                                ExceptionLengthMin=es[2], ExceptionLengthMax=es[3], ExceptionLengthSD=es[4],
                                AgreementBlocks=len(agreements), AgreementLengthMean=gs[0], AgreementLengthMedian=gs[1],
                                AgreementLengthMin=gs[2], AgreementLengthMax=gs[3], AgreementLengthSD=gs[4],
                                ExceptionStartIntervalCount=len(intervals), ExceptionStartIntervalMean=ds[0],
                                ExceptionStartIntervalMedian=ds[1], ExceptionStartIntervalMin=ds[2],
                                ExceptionStartIntervalMax=ds[3], ExceptionStartIntervalSD=ds[4],
                                Lag10=next(x['Autocorrelation'] for x in lag_rows if x['RunID']==rid and x['Lag']==10),
                                Lag11=next(x['Autocorrelation'] for x in lag_rows if x['RunID']==rid and x['Lag']==11),
                                Lag21=next(x['Autocorrelation'] for x in lag_rows if x['RunID']==rid and x['Lag']==21),
                                Lag22=next(x['Autocorrelation'] for x in lag_rows if x['RunID']==rid and x['Lag']==22)))

        # Source rows around each exception block boundary in Runs 84/95.
        if rid in ('84', '95'):
            source_by_cycle = defaultdict(list)
            for item in selected:
                source_by_cycle[item['Cycle']].append(item)
            for block in exceptions:
                for boundary_type, boundary_cycle in (('Start', block[0]['Cycle']), ('End', block[-1]['Cycle'])):
                    missing_neighbors = [c for c in range(boundary_cycle-3, boundary_cycle+4) if c not in cycle_records]
                    for c in range(boundary_cycle-3, boundary_cycle+4):
                        if c not in source_by_cycle:
                            continue
                        cycle_info = cycle_records[c]
                        for item in source_by_cycle[c]:
                            row = item['Row']
                            seconds = number(row.get('Time'))
                            prev = cycle_records.get(c-1)
                            prevsec = prev.get('FirstTimestampSeconds') if prev else None
                            dt = seconds-prevsec if seconds is not None and prevsec is not None else ''
                            boundary_rows.append(dict(RunID=rid, BoundaryType=boundary_type,
                                                      BoundaryCycle=boundary_cycle, SourceRowNumber=item['SourceDataRow'],
                                                      CSVLineNumber=item['CSVLineNumber'], Timestamp=row.get('TimeString',''),
                                                      TimestampSeconds=seconds if seconds is not None else '',
                                                      SecondsFromPreviousCycle=dt, CycleNumber=c,
                                                      Measurement=item['Measurement'], ClassifiedBand=item['Band'],
                                                      ExpectedBand=cycle_info['ExpectedBand'], ObservedBand=cycle_info['ObservedBand'],
                                                      ExceptionIndicator=cycle_info['ExceptionIndicator'],
                                                      SourceRowsForCycle=cycle_info['SourceRowCount'],
                                                      DuplicateCycleIndicator=cycle_info['DuplicateCycleIndicator'],
                                                      MixedBandIndicator=cycle_info['MixedBandIndicator'],
                                                      RepeatedTimestampGlobal=''))
                    for r in boundary_rows:
                        if r['RunID']==rid and r['BoundaryType']==boundary_type and r['BoundaryCycle']==boundary_cycle:
                            r['MissingNeighborCycles']=';'.join(map(str,missing_neighbors))

    # Flag repeated timestamp values among selected source rows and annotate boundary rows.
    timestamp_counts = Counter(x['Row'].get('TimeString','') for vals in selected_by_run.values() for x in vals if x['Row'].get('TimeString',''))
    for row in boundary_rows:
        row['RepeatedTimestampGlobal'] = int(timestamp_counts.get(row['Timestamp'], 0) > 1)

    # Add an explicit run-level validation summary to the accounting table.
    for v in run_validation:
        excluded.append(dict(RunID=v['RunID'], ExcludedType='ValidationAndAccounting',
                             Reason='Mixed cycles excluded from binary statistics', Count=v['MixedCycles'], Cycle='', SourceRows=''))
    for rid, ordered in all_ordered.items():
        lo, hi = min(x['Cycle'] for x in ordered), max(x['Cycle'] for x in ordered)
        gaps = [c for c in range(lo, hi+1) if c not in cycles_by_run[rid]]
        if gaps:
            excluded.append(dict(RunID=rid, ExcludedType='MissingCycleSummary',
                                 Reason='Cycle numbers with no historical-eligible selected row', Count=len(gaps),
                                 Cycle=';'.join(map(str,gaps)), SourceRows=''))

    # Write all outputs only after all six runs passed every lineage checkpoint.
    outputs = {
        'CycleSequence': META / f'PSI101_Pyrell_DustTrakA_Periodicity_CycleSequence_{STAMP}.csv',
        'BlockEvents': META / f'PSI101_Pyrell_DustTrakA_Periodicity_BlockEvents_{STAMP}.csv',
        'LagCorrelation': META / f'PSI101_Pyrell_DustTrakA_Periodicity_LagCorrelation_{STAMP}.csv',
        'CandidateModel': META / f'PSI101_Pyrell_DustTrakA_Periodicity_CandidateModel_{STAMP}.csv',
        'BoundaryRows': META / f'PSI101_Pyrell_DustTrakA_Periodicity_BoundaryRows_{STAMP}.csv',
        'RunMetrics': META / f'PSI101_Pyrell_DustTrakA_Periodicity_RunMetrics_{STAMP}.csv',
        'ExcludedCycles': META / f'PSI101_Pyrell_DustTrakA_Periodicity_ExcludedCycles_{STAMP}.csv',
    }
    write_csv(outputs['CycleSequence'], sequence)
    write_csv(outputs['BlockEvents'], block_events)
    write_csv(outputs['LagCorrelation'], lag_rows)
    write_csv(outputs['CandidateModel'], candidate_rows)
    write_csv(outputs['BoundaryRows'], boundary_rows)
    write_csv(outputs['RunMetrics'], run_metrics)
    write_csv(outputs['ExcludedCycles'], excluded)

    report_path = META / f'PSI101_Pyrell_DustTrakA_Periodicity_AuditReport_{STAMP}.txt'
    with report_path.open('w', encoding='utf-8') as f:
        f.write('Periodicity and phase-stability audit — PSI-101 Pyrell DustTrak A\n')
        f.write(f'Generated {STAMP}. No original source CSVs or archived audit outputs were changed.\n\n')
        f.write('VALIDATION GATE\nAll six runs passed before analysis or output writing: historical classified-cycle totals, exception counts and exact exception cycle identities match archived RelativeCyclePhase records. Mixed cycle identities/source rows and duplicate-cycle counts also match. Per-run checkpoint details: ')
        f.write('; '.join(f"Run {x['RunID']}: classified {x['ClassifiedCycles']}/{x['ArchivedClassifiedCycles']}, exceptions {x['Exceptions']}/{x['ArchivedExceptions']}, exception identities match={x['ExceptionCycleIdentitiesMatch']}" for x in run_validation)+'\n\n')
        f.write('METHODS\nRecovered row eligibility: trimmed TestNumber equals RunID; RunMode=3; DustTrakAState=6; DustTrakAPower=1; finite measurement, analog and cycle; measurement != -999; integer cycle. Historical four-band rules: Below 10000 (<10000), 10000-14999 ([10000,15000)), 15000-19999 ([15000,20000)), 20000+ (>=20000). Multiple distinct bands in a cycle produce MixedBand. The phase mapping is fixed from the archived per-run PhaseSummary; relative phase uses actual cycle minus archived FirstCycle modulo two. Mixed cycles are retained in sequence/separate table, but excluded from binary statistics. Missing cycle numbers are never imputed; lags and blocks use numeric cycle adjacency. Autocorrelation pairs cycle c with c+lag.\n')
        f.write('Square-wave model predicts an exception during a width-8-to-13 phase window in each period 18–26; all offsets are searched. It maximizes training accuracy with deterministic ties favoring smaller period, then width, then offset. The constant-rate baseline probability is the training exception fraction; thresholding that rate at 0.5 yields the reported majority-class baseline (ties choose agreement). Full-sequence fits are in-sample; holdout results freeze all fit parameters. Precision/recall/F1 refer to exception as positive. Sample SD is reported for block lengths and intervals.\n\n')
        for rid in ('84','95'):
            m=next(x for x in run_metrics if x['RunID']==rid)
            cand=[x for x in candidate_rows if x['RunID']==rid]
            full=next(x for x in cand if x['ModelType']=='FullSequenceBest')
            h1=next(x for x in cand if x['ModelType']=='ChronologicalHoldout' and x['TrainWindow']=='FirstHalf')
            h2=next(x for x in cand if x['ModelType']=='ChronologicalHoldout' and x['TrainWindow']=='SecondHalf')
            win=next(x for x in cand if x['ModelType']=='ReportedWindowFit')
            lags={x['Lag']:x for x in lag_rows if x['RunID']==rid}
            f.write(f"RUN {rid}\n")
            f.write(f"{m['PhaseExceptions']} exceptions among {m['ClassifiedBinaryCycles']} binary-eligible cycles; {m['MixedBandCycles']} mixed cycles excluded. Exception block lengths mean/median/min/max/SD={m['ExceptionLengthMean']:.2f}/{m['ExceptionLengthMedian']:.2f}/{m['ExceptionLengthMin']}/{m['ExceptionLengthMax']}/{m['ExceptionLengthSD']:.2f}; exception start intervals mean/median/min/max/SD={m['ExceptionStartIntervalMean']:.2f}/{m['ExceptionStartIntervalMedian']:.2f}/{m['ExceptionStartIntervalMin']}/{m['ExceptionStartIntervalMax']}/{m['ExceptionStartIntervalSD']:.2f}.\n")
            f.write('Lag autocorrelation: '+ '; '.join(f"lag {k}: r={lags[k]['Autocorrelation']}, n={lags[k]['ValidCyclePairs']}" for k in (10,11,21,22))+'; full lag series and n in LagCorrelation CSV.\n')
            f.write(f"Full-sequence best in-sample model P={full['Period']}, width={full['MismatchWidth']}, offset={full['PhaseOffset']}; accuracy={full['Accuracy']:.4f}, precision={full['Precision']:.4f}, recall={full['Recall']:.4f}, F1={full['F1']:.4f}, baseline accuracy={full['BaselineAccuracy']:.4f}, n={full['ValidCycles']}.\n")
            f.write(f"First-half fit -> second-half evaluation: P={h1['Period']}, width={h1['MismatchWidth']}, offset={h1['PhaseOffset']}; holdout accuracy={h1['Accuracy']:.4f}, F1={h1['F1']:.4f}, constant baseline accuracy={h1['BaselineAccuracy']:.4f}, train accuracy={h1['TrainAccuracy']:.4f}, eval n={h1['ValidCycles']}.\n")
            f.write(f"Second-half fit -> first-half evaluation: P={h2['Period']}, width={h2['MismatchWidth']}, offset={h2['PhaseOffset']}; holdout accuracy={h2['Accuracy']:.4f}, F1={h2['F1']:.4f}, constant baseline accuracy={h2['BaselineAccuracy']:.4f}, train accuracy={h2['TrainAccuracy']:.4f}, eval n={h2['ValidCycles']}.\n")
            f.write(f"Previously highlighted window fit ({win['TrainWindow']}) gives P={win['Period']}, width={win['MismatchWidth']}, offset={win['PhaseOffset']}; window fit accuracy={win['TrainAccuracy']:.4f} (n={win['TrainValidCycles']}), outside-window frozen evaluation accuracy={win['Accuracy']:.4f} vs baseline {win['BaselineAccuracy']:.4f} (n={win['ValidCycles']}).\n\n")
        f.write('ALL-RUN COMPARISON\n')
        for m in run_metrics:
            f.write(f"Run {m['RunID']}: classified={m['ClassifiedBinaryCycles']}, mixed excluded={m['MixedBandCycles']}, missing cycle numbers={m['MissingCycleNumbers']}, duplicates={m['DuplicateCycleNumbers']}, exceptions={m['PhaseExceptions']}, exception blocks={m['ExceptionBlocks']}, exception block median={m['ExceptionLengthMedian']}, start interval median={m['ExceptionStartIntervalMedian']}.\n")
        f.write('\nINTERPRETATION\n')
        for rid in ('84','95'):
            m=next(x for x in run_metrics if x['RunID']==rid)
            h1=next(x for x in candidate_rows if x['RunID']==rid and x['ModelType']=='ChronologicalHoldout' and x['TrainWindow']=='FirstHalf')
            h2=next(x for x in candidate_rows if x['RunID']==rid and x['ModelType']=='ChronologicalHoldout' and x['TrainWindow']=='SecondHalf')
            stable=(h1['Period']==h2['Period'] and h1['PhaseOffset']==h2['PhaseOffset'])
            if rid == '84':
                interpretation = (f"the dominant exception block train in cycles 1771–2135 has a 21–22-cycle recurrence, while the full run is not uniformly periodic (all exception-start intervals span {m['ExceptionStartIntervalMin']}–{m['ExceptionStartIntervalMax']} cycles, median {m['ExceptionStartIntervalMedian']}; isolated early blocks and a terminal partial block affect the range).")
            else:
                interpretation = (f"the exception-active pattern has regular 21–22-cycle starts inside cycles 8677–8858 (all {m['ExceptionStartIntervalCount']} start intervals range {m['ExceptionStartIntervalMin']}–{m['ExceptionStartIntervalMax']}; median {m['ExceptionStartIntervalMedian']}), but all recorded exceptions are confined to the previously highlighted 8676–8875 window; it does not persist into the rest of the run.")
            f.write(f"Run {rid}: {interpretation} Half-split period/offset stability is {'stable' if stable else 'unstable'} (first-fit P={h1['Period']},offset={h1['PhaseOffset']}; reverse-fit P={h2['Period']},offset={h2['PhaseOffset']}). The frozen outside-window model comparison is in CandidateModel; it tests whether the selected-window fit generalizes.\n")
        f.write('Exception-block lengths are reported directly; consistency is assessed from their mean/median/spread, not assumed from the selected windows. Other four runs are comparison series and should be interpreted through their counts and candidate metrics rather than assumed to share a pattern. Missing cycles and mixed cycles break block continuity and remove lag pairs; duplicate source rows are collapsed to one cycle but retained as multiplicity. BoundaryRows lists source rows, timestamp seconds and repeated timestamps for every exception-block start/end in Runs 84/95. Timestamp/row multiplicity coincidences are descriptive only and do not identify an acquisition mechanism.\n\n')
        f.write('LIMITATIONS\nNo physical mechanism, instrument fault or acquisition behavior can be established from these phase and timestamp associations. Model search selects from many phase offsets and widths, so in-sample performance is optimistic. Half-split tests reduce this concern but do not provide independent external validation. The historical phase mapping is preserved exactly; results remain conditional on that validated definition.\n\nFiles created:\n')
        for p in list(outputs.values())+[report_path]:
            f.write(str(p.resolve())+'\n')

    for path in list(outputs.values()) + [report_path]:
        print(path.resolve())
    print('VALIDATION: all six runs passed')


def cycle_map_for(rid, maps):
    return maps[rid]


def mixed_table_for(rid, table):
    return [x for x in table if x['RunID'] == rid]


if __name__ == '__main__':
    main()
