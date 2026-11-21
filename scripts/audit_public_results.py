"""Validate every saved run and telemetry event, then save compact reviewable evidence.

Run from the repository: python3 scripts/audit_public_results.py results/public-18-1000
Assertions are intentional experiment self-checks; do not run with python -O.
"""
import csv
import gzip
import hashlib
import json
import math
import shutil
import statistics
import sys
from collections import defaultdict
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jssp.core import decode,load,validate
from jssp.algorithms import DEFAULTS
from jssp.benchmarks import verify_sources
from jssp.__main__ import write_csv


def audit(raw, target=ROOT/'experiments/public-18'):
    raw,target=Path(raw),Path(target)
    protocol=json.loads((target/'protocol.json').read_text())
    metadata=json.loads((raw/'metadata.json').read_text())
    rows=list(csv.DictReader((raw/'runs.csv').open()))
    summary=list(csv.DictReader((raw/'summary.csv').open()))
    instances,_=verify_sources()
    inputs={i.name:i for i in instances}
    budget=protocol['budget']
    expected={(name,alg,seed) for name in protocol['instances'] for alg in protocol['algorithms'] for seed in protocol['seeds']}
    actual={(r['instance'],r['algorithm'],int(r['seed'])) for r in rows}
    assert len(rows)==len(expected)==len(actual) and actual==expected, 'incomplete or duplicate runs'
    assert metadata['failures']==0 and not (raw/'failures.jsonl').read_text(), 'recorded failures'
    assert metadata['parameter_overrides']==protocol['parameter_overrides']=={}, 'unexpected parameter overrides'
    assert protocol['parameters']==DEFAULTS, 'parameter defaults changed'
    assert metadata['arguments']['budget']==budget and metadata['arguments']['repeats']==len(protocol['seeds'])
    assert metadata['arguments']['seed']==protocol['seeds'][0]
    for record in metadata['inputs']:
        path=ROOT/record['path']
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'], 'input changed'
    assert len(metadata['inputs'])==len(inputs)
    assert {record['instance']['name'] for record in metadata['inputs']}==set(inputs)
    checkpoints=[1]+list(range(100,budget+1,100))
    convergence=defaultdict(list)
    best={};run_rows={r['run_id']:r for r in rows};raw_hashes={}
    target.mkdir(parents=True,exist_ok=True)
    solutions=target/'solutions.jsonl.gz'
    # Fixed gzip timestamp keeps the evidence archive reproducible.
    with solutions.open('wb') as binary, gzip.GzipFile(filename='',fileobj=binary,mode='wb',mtime=0) as archive:
        for row in rows:
            run_id=row['run_id'];path=raw/(run_id+'.json');content=path.read_bytes()
            raw_hashes[path.name]=hashlib.sha256(content).hexdigest()
            result=json.loads(content);inst=inputs[result['instance']]
            assert (result['instance'],result['algorithm'],result['seed'])==(row['instance'],row['algorithm'],int(row['seed']))
            assert result['parameters']==protocol['parameters']
            assert result['budget']==budget==len(result['history'])==int(row['evaluations'])
            makespan,schedule=decode(inst,result['sequence']);validate(inst,result['schedule'])
            assert schedule==result['schedule'] and makespan==result['makespan']==int(row['makespan'])
            assert makespan>=inst.bks, 'result below verified optimum'
            rpd=100*(makespan-inst.bks)/inst.bks
            assert math.isclose(rpd,result['rpd'],abs_tol=1e-10) and math.isclose(rpd,float(row['rpd']),abs_tol=1e-10)
            assert result['runtime_seconds']==float(row['runtime_seconds'])
            running_best=math.inf;last_elapsed=0.
            for k,event in enumerate(result['history'],1):
                running_best=min(running_best,event['current'])
                assert event['evaluation']==k and event['best']==running_best
                assert event['elapsed_seconds']>=last_elapsed
                last_elapsed=event['elapsed_seconds']
            assert running_best==makespan and last_elapsed<=result['runtime_seconds']
            for k in checkpoints:
                convergence[inst.name,result['algorithm'],k].append(result['history'][k-1]['best'])
            key=(inst.name,result['algorithm'])
            if key not in best or makespan<best[key]['makespan']: best[key]=result
            saved={k:result[k] for k in ('run_id','instance','algorithm','seed','budget','parameters','makespan','rpd','sequence','schedule','runtime_seconds')}
            archive.write((json.dumps(saved,separators=(',',':'))+'\n').encode())
    count=0;seen=set();current_id=None;position=0
    with (raw/'telemetry.jsonl').open() as stream:
        for line in stream:
            event=json.loads(line);run_id=event['run_id']
            if run_id!=current_id:
                assert current_id is None or position==budget, 'truncated telemetry run'
                assert run_id not in seen, 'repeated telemetry run'
                seen.add(run_id);current_id=run_id;position=0
                result=json.loads((raw/(run_id+'.json')).read_text())
            assert event['instance']==result['instance'] and event['algorithm']==result['algorithm'] and event['seed']==result['seed']
            assert {key:event[key] for key in result['history'][position]}==result['history'][position], 'telemetry and saved history differ'
            position+=1;count+=1
    assert position==budget and seen==set(run_rows) and count==len(expected)*budget
    for row in summary:
        group=[r for r in rows if r['instance']==row['instance'] and r['algorithm']==row['algorithm']]
        values=[int(r['makespan']) for r in group]
        assert int(row['runs'])==len(protocol['seeds'])
        expected_summary=dict(best=min(values),mean=statistics.mean(values),median=statistics.median(values),stdev=statistics.stdev(values),
                              mean_runtime_seconds=statistics.mean(float(r['runtime_seconds']) for r in group),
                              mean_rpd=statistics.mean(float(r['rpd']) for r in group))
        assert all(math.isclose(float(row[key]),value,abs_tol=1e-10) for key,value in expected_summary.items())
    assert len(summary)==len(inputs)*len(protocol['algorithms'])
    assert {(row['instance'],row['algorithm']) for row in summary}==set(best)
    baselines=json.loads((raw/'baselines.json').read_text())
    assert len(baselines)==len(inputs)
    for base in baselines:
        inst=inputs[base['instance']];validate(inst,base['schedule'])
        assert decode(inst,base['sequence'])==(base['makespan'],base['schedule'])
    convergence_rows=[]
    for (name,alg,k),values in sorted(convergence.items()):
        convergence_rows.append(dict(instance=name,algorithm=alg,evaluation=k,runs=len(values),mean_best=statistics.mean(values),
                                     mean_rpd=100*(statistics.mean(values)-inputs[name].bks)/inputs[name].bks))
    write_csv(target/'convergence.csv',convergence_rows)
    for name in ('runs.csv','summary.csv','metadata.json','baselines.json','failures.jsonl'):
        shutil.copyfile(raw/name,target/name)
    with (target/'best-runs.json.gz').open('wb') as binary, gzip.GzipFile(filename='',fileobj=binary,mode='wb',mtime=0) as archive:
        archive.write(json.dumps(list(best.values()),separators=(',',':')).encode())
    for name in ('runs.csv','summary.csv','metadata.json','baselines.json','failures.jsonl','telemetry.jsonl','report.html'):
        digest=hashlib.sha256()
        with (raw/name).open('rb') as binary:
            for chunk in iter(lambda: binary.read(1024*1024), b''):
                digest.update(chunk)
        raw_hashes[name]=digest.hexdigest()
    audit_record=dict(runs=len(rows),instances=len(inputs),seeds_per_algorithm=len(protocol['seeds']),evaluations_per_run=budget,
                      candidate_evaluations=count,failures=0,validated_schedules=len(rows),source_revision=metadata['revision'],
                      raw_output_directory=str(raw),raw_sha256=raw_hashes,
                      checks=['All 18 source datasets and both BKS catalogues agree','All 1,440 algorithm/instance/seed combinations present',
                              'All parameters and evaluation budgets equal the frozen protocol','Every best schedule validated and reproduced from its priority list',
                              'All per-evaluation telemetry matches saved histories','All CSV summary statistics independently recomputed'])
    (target/'audit.json').write_text(json.dumps(audit_record,indent=2)+'\n')
    print(f'Audited {len(rows)} runs and {count} candidate evaluations; saved evidence to {target}')

if __name__=='__main__':
    if not __debug__: raise RuntimeError('Run without -O so audit assertions execute')
    audit(Path(sys.argv[1]) if len(sys.argv)>1 else ROOT/'results/public-18-1000')
