"""python3 -m jssp --help"""
import argparse
import csv
import hashlib
import json
import platform
import statistics
import subprocess
import sys
import traceback
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from .algorithms import solve
from .core import load, load_orlib, decode, spt, validate
from .report import write_report


def write_csv(path, rows):
    if not rows: return
    with path.open('w',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)


def main(argv=None):
    parser=argparse.ArgumentParser(description='Compare GA, DPSO, ACO and SA using equal candidate-evaluation budgets.')
    parser.add_argument('--instances',nargs='+',default=['instances/crossed.json'])
    parser.add_argument('--algorithms',nargs='+',choices=['ga','dpso','aco','sa'],default=['ga','dpso','aco','sa'])
    parser.add_argument('--budget',type=int,default=1000)
    parser.add_argument('--repeats',type=int,default=20)
    parser.add_argument('--seed',type=int,default=0)
    parser.add_argument('--parameters',type=Path,help='JSON mapping algorithm names to parameter overrides')
    parser.add_argument('--orlib-name',help='Named instance in one OR-Library jobshop1 file; BKS left unset')
    parser.add_argument('--output',type=Path,help='New output directory; existing directories are refused')
    parser.add_argument('--quiet',action='store_true')
    args=parser.parse_args(argv)
    if args.budget<1 or args.repeats<1: parser.error('budget and repeats must be positive')
    if args.orlib_name and len(args.instances)!=1: parser.error('OR-Library mode requires exactly one file')
    output=args.output or Path('results')/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    output.mkdir(parents=True,exist_ok=False)
    try: revision=subprocess.check_output(['git','rev-parse','HEAD'],stderr=subprocess.DEVNULL,text=True).strip()
    except (OSError,subprocess.CalledProcessError): revision=None
    metadata=dict(created_utc=datetime.now(timezone.utc).isoformat(),python=sys.version,platform=platform.platform(),
                  processor=platform.processor(),revision=revision,arguments=vars(args).copy(),inputs=[])
    metadata['arguments']={k:str(v) if isinstance(v,Path) else v for k,v in metadata['arguments'].items()}
    params=json.loads(args.parameters.read_text()) if args.parameters else {}
    if not isinstance(params,dict) or set(params)-{'ga','dpso','aco','sa'}: parser.error('invalid parameter file')
    metadata['parameter_overrides']=params
    runs=[];summaries=[];baselines=[];failures=0
    last_report=perf_counter()
    print(f'Report: {output.resolve()/"report.html"}',flush=True)
    write_report(output/'report.html',runs,True)
    with (output/'telemetry.jsonl').open('w') as telemetry, (output/'failures.jsonl').open('w') as errors:
        for index,path in enumerate(args.instances):
            try:
                raw=Path(path).read_bytes()
                inst=load_orlib(path,args.orlib_name) if args.orlib_name else load(path)
                metadata['inputs'].append(dict(path=path,sha256=hashlib.sha256(raw).hexdigest(),instance=asdict(inst)))
                base_score,base_ops=decode(inst,spt(inst));validate(inst,base_ops)
                baselines.append(dict(instance=inst.name,input_index=index,makespan=base_score,sequence=spt(inst),schedule=base_ops))
            except Exception as exc:
                failures+=1;errors.write(json.dumps(dict(input=path,error=str(exc),traceback=traceback.format_exc()))+'\n');errors.flush();continue
            for alg in args.algorithms:
                for seed in range(args.seed,args.seed+args.repeats):
                    run_id=f'{index}-{alg}-{seed}';last_refresh=[0.];partial=[]
                    def progress(event):
                        nonlocal last_report
                        best_sequence=event.pop('best_sequence')
                        telemetry.write(json.dumps(dict(run_id=run_id,instance=inst.name,algorithm=alg,seed=seed,**event))+'\n');telemetry.flush()
                        partial.append(event)
                        if event['evaluation']==1 or event['evaluation']==args.budget or perf_counter()-last_refresh[0]>.5:
                            if not args.quiet:
                                print(f'{inst.name} {alg.upper()} seed={seed} evaluations={event["evaluation"]}/{args.budget} best={event["best"]}',flush=True)
                            last_refresh[0]=perf_counter()
                        if perf_counter()-last_report >= 2:
                            preview=dict(instance=inst.name,algorithm=alg,seed=seed,input_index=index,makespan=event['best'],rpd=None,runtime_seconds=event['elapsed_seconds'],history=partial,budget=args.budget,schedule=decode(inst,best_sequence)[1])
                            write_report(output/'report.html',runs+[preview],True)
                            last_report=perf_counter()
                    try:
                        result=solve(inst,alg,args.budget,seed,progress,**params.get(alg,{}))
                        result.update(instance=inst.name,run_id=run_id,input_index=index)
                        (output/f'{run_id}.json').write_text(json.dumps(result,indent=2)+'\n')
                        # Full histories are already saved; retain only chart samples between runs.
                        history=result['history']
                        step=max(1,(len(history)+199)//200)
                        sampled=history[::step]
                        if sampled[-1] is not history[-1]: sampled.append(history[-1])
                        runs.append(result | dict(history=sampled,evaluations=len(history),
                                                  history_max=max(row['current'] for row in history)))
                        summaries.append(dict(run_id=run_id,instance=inst.name,input_index=index,jobs=len(inst.jobs),machines=inst.machines,
                                              ratio=len(inst.jobs)/inst.machines,algorithm=alg,seed=seed,makespan=result['makespan'],
                                              rpd=result['rpd'],runtime_seconds=result['runtime_seconds'],evaluations=len(result['history'])))
                    except Exception as exc:
                        failures+=1;errors.write(json.dumps(dict(run_id=run_id,input=path,error=str(exc),traceback=traceback.format_exc()))+'\n');errors.flush()
                    write_csv(output/'runs.csv',summaries)
                    if perf_counter()-last_report >= 2:
                        write_report(output/'report.html',runs,True)
                        last_report=perf_counter()
    aggregates=[]
    for index in range(len(args.instances)):
        for alg in args.algorithms:
            group=[r for r in summaries if r['input_index']==index and r['algorithm']==alg]
            if not group: continue
            values=[r['makespan'] for r in group];rpds=[r['rpd'] for r in group if r['rpd'] is not None]
            aggregates.append(dict(instance=group[0]['instance'],input_index=index,algorithm=alg,runs=len(group),best=min(values),
                                   mean=statistics.mean(values),median=statistics.median(values),stdev=statistics.stdev(values) if len(values)>1 else 0.,
                                   mean_runtime_seconds=statistics.mean(r['runtime_seconds'] for r in group),mean_rpd=statistics.mean(rpds) if rpds else None))
    write_csv(output/'summary.csv',aggregates)
    (output/'baselines.json').write_text(json.dumps(baselines,indent=2)+'\n')
    metadata['failures']=failures
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    write_report(output/'report.html',runs)
    print(f'Finished: {len(runs)} successful runs, {failures} failures. Results: {output.resolve()}',flush=True)
    return 1 if failures else 0

if __name__=='__main__': raise SystemExit(main())
