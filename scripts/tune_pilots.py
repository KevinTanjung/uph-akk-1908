"""Equal-budget configuration selection using only the separate pilot instances."""
import argparse
import csv
import gzip
import hashlib
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jssp.algorithms import DEFAULTS
from jssp.core import load,decode,validate
from jssp.__main__ import write_csv


def validate_plan(plan):
    if set(plan['instances']) & set(plan['excluded_final_instances']):
        raise ValueError('pilot and final instances overlap')
    if set(plan['seeds']) & set(range(20)):
        raise ValueError('pilot seeds overlap final evaluation seeds')
    if plan['parameters']!=DEFAULTS or set(plan['algorithms'])!={'ga','dpso','aco','sa'}:
        raise ValueError('unexpected algorithms or base defaults')
    counts={len(plan['configurations'][alg]) for alg in plan['algorithms']}
    if len(counts)!=1 or min(counts)<2:
        raise ValueError('algorithms must receive the same number of configurations')
    for alg in plan['algorithms']:
        if plan['configurations'][alg][0]!={}:
            raise ValueError('configuration zero must be the defaults')
        for cfg in plan['configurations'][alg]:
            if not isinstance(cfg,dict) or set(cfg)-DEFAULTS.keys():
                raise ValueError('unknown configuration parameter')


def select(trials,plan):
    validate_plan(plan)
    expected={(alg,cfg,name,seed) for alg in plan['algorithms']
              for cfg in range(len(plan['configurations'][alg]))
              for name in plan['instances'] for seed in plan['seeds']}
    actual={(r['algorithm'],r['configuration'],r['instance'],r['seed']) for r in trials}
    if len(actual)!=len(trials) or actual!=expected:
        raise ValueError('missing, duplicate or unexpected pilot trials')
    if any(r['evaluations']!=plan['budget'] for r in trials):
        raise ValueError('unequal evaluation budgets')
    scores=[];selected={};chosen={}
    for alg in plan['algorithms']:
        exact=[]
        for cfg in range(len(plan['configurations'][alg])):
            group=[r for r in trials if r['algorithm']==alg and r['configuration']==cfg]
            score=sum(Fraction(100*(r['makespan']-r['bks']),r['bks']) for r in group)/len(group)
            exact.append(score)
            scores.append(dict(algorithm=alg,configuration=cfg,runs=len(group),mean_rpd=float(score),exact_score=str(score)))
        winner=min(range(len(exact)),key=exact.__getitem__)
        chosen[alg]=winner;selected[alg]=plan['configurations'][alg][winner]
    for row in scores:row['selected']=row['configuration']==chosen[row['algorithm']]
    return selected,chosen,scores


def tune(plan_path,output,target,workers=4,resume=False):
    plan_path,output,target=Path(plan_path),Path(output),Path(target)
    plan=json.loads(plan_path.read_text());validate_plan(plan)
    if plan['seeds']!=list(range(plan['seeds'][0],plan['seeds'][0]+len(plan['seeds']))) or workers<1:
        raise ValueError('consecutive pilot seeds and positive worker count required')
    pilots={name:load(ROOT/'instances/pilot'/(name+'.json')) for name in plan['instances']}
    output.mkdir(parents=True,exist_ok=resume)
    snapshot=output/'plan.json'
    if snapshot.exists() and json.loads(snapshot.read_text())!=plan:
        raise ValueError('the saved tuning plan differs')
    snapshot.write_text(json.dumps(plan,indent=2)+'\n')
    (output/'jobs').mkdir(exist_ok=True);(output/'configurations').mkdir(exist_ok=True)
    jobs=[]
    for alg in plan['algorithms']:
        for cfg,overrides in enumerate(plan['configurations'][alg]):
            path=output/'configurations'/f'{alg}-{cfg}.json'
            path.write_text(json.dumps({alg:overrides},indent=2)+'\n')
            jobs.extend((alg,cfg,name,path) for name in plan['instances'])
    # Larger pilot instances start first to reduce the final waiting time.
    jobs.sort(key=lambda job:len(pilots[job[2]].sequence),reverse=True)
    def run(job):
        alg,cfg,name,path=job;folder=output/'jobs'/f'{alg}-{cfg}-{name}'
        if resume and (folder/'metadata.json').exists():
            meta=json.loads((folder/'metadata.json').read_text())
            if meta['failures']==0 and meta['parameter_overrides']=={alg:plan['configurations'][alg][cfg]}:
                return job
        command=[sys.executable,'-m','jssp','--instances','instances/pilot/'+name+'.json',
                 '--algorithms',alg,'--budget',str(plan['budget']),'--repeats',str(len(plan['seeds'])),
                 '--seed',str(plan['seeds'][0]),'--parameters',str(path),'--quiet','--output',str(folder)]
        if resume and folder.exists():command.append('--resume')
        with (output/'jobs'/f'{alg}-{cfg}-{name}.log').open('a') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        return job
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures=[pool.submit(run,job) for job in jobs]
        for count,future in enumerate(as_completed(futures),1):
            alg,cfg,name,_=future.result()
            print(f'Pilot job {count}/{len(jobs)}: {alg} configuration {cfg}, {name}',flush=True)
    trials=[];hashes={};solutions=[];telemetry_events=0
    for alg,cfg,name,_ in jobs:
        folder=output/'jobs'/f'{alg}-{cfg}-{name}';inst=pilots[name]
        meta=json.loads((folder/'metadata.json').read_text())
        assert meta['failures']==0 and not (folder/'failures.jsonl').read_text()
        assert meta['inputs'][0]['sha256']==hashlib.sha256((ROOT/'instances/pilot'/(name+'.json')).read_bytes()).hexdigest()
        histories={}
        for seed in plan['seeds']:
            path=folder/f'0-{alg}-{seed}.json';content=path.read_bytes();r=json.loads(content)
            assert r['algorithm']==alg and r['instance']==name and r['seed']==seed
            assert r['parameters']==(DEFAULTS | plan['configurations'][alg][cfg])
            assert r['budget']==len(r['history'])==plan['budget']
            assert decode(inst,r['sequence'])==(r['makespan'],r['schedule']);validate(inst,r['schedule'])
            assert r['makespan']>=inst.bks
            best=float('inf')
            for evaluation,event in enumerate(r['history'],1):
                best=min(best,event['current'])
                assert event['evaluation']==evaluation and event['best']==best
            assert best==r['makespan']
            assert abs(r['rpd']-100*(r['makespan']-inst.bks)/inst.bks)<1e-10
            row=dict(algorithm=alg,configuration=cfg,instance=name,seed=seed,makespan=r['makespan'],bks=inst.bks,
                     rpd=100*(r['makespan']-inst.bks)/inst.bks,evaluations=len(r['history']),runtime_seconds=r['runtime_seconds'])
            trials.append(row);histories[f'0-{alg}-{seed}']=r['history']
            hashes[str(path.relative_to(output))]=hashlib.sha256(content).hexdigest()
            solutions.append(row | dict(sequence=r['sequence'],schedule=r['schedule']))
        counts={key:0 for key in histories}
        with (folder/'telemetry.jsonl').open() as stream:
            for line in stream:
                event=json.loads(line);key=event['run_id'];expected=histories[key][counts[key]]
                assert {field:event[field] for field in expected}==expected
                assert event['algorithm']==alg and event['instance']==name and event['seed']==int(key.rsplit('-',1)[1])
                counts[key]+=1;telemetry_events+=1
        assert all(count==plan['budget'] for count in counts.values())
    selected,chosen,scores=select(trials,plan)
    target.mkdir(parents=True,exist_ok=True)
    write_csv(target/'trials.csv',trials);write_csv(target/'scores.csv',scores)
    (target/'parameters.json').write_text(json.dumps(selected,indent=2)+'\n')
    record=dict(selected_configurations=chosen,parameter_overrides=selected,scores=scores,
                pilot_instances=plan['instances'],pilot_seeds=plan['seeds'],trials=len(trials),
                candidate_evaluations=telemetry_events,failures=0,plan_sha256=hashlib.sha256(plan_path.read_bytes()).hexdigest(),
                pilot_sha256={name:hashlib.sha256((ROOT/'instances/pilot'/(name+'.json')).read_bytes()).hexdigest() for name in pilots},
                selection_rule=plan['selection'],raw_output_directory=str(output),raw_run_sha256=hashes,
                checks=['Every trial and telemetry record validated','Equal candidate counts and evaluation budgets for all algorithms',
                        'Pilot instance names and seeds excluded from final benchmark selection'])
    (target/'selection.json').write_text(json.dumps(record,indent=2)+'\n')
    with (target/'solutions.jsonl.gz').open('wb') as stream,gzip.GzipFile(filename='',fileobj=stream,mode='wb',mtime=0) as archive:
        for row in solutions:archive.write((json.dumps(row,separators=(',',':'))+'\n').encode())
    print(json.dumps(dict(trials=len(trials),evaluations=telemetry_events,chosen=chosen,parameters=selected),indent=2),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plan',type=Path,default=ROOT/'experiments/pilot-tuning/plan.json')
    parser.add_argument('--output',type=Path,default=ROOT/'results/pilot-tuning')
    parser.add_argument('--evidence',type=Path,default=ROOT/'experiments/pilot-tuning')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args();tune(args.plan,args.output,args.evidence,args.workers,args.resume)
