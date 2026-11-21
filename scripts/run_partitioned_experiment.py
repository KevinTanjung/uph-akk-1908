"""Run independent public instances in separate processes, then merge their evidence."""
import argparse
import csv
import json
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from jssp.__main__ import write_csv
from jssp.algorithms import DEFAULTS
from jssp.benchmarks import NAMES
from jssp.core import load
from jssp.report import write_report


def merge(output, protocol, workers, resumed=False):
    runs=[];rows=[];summaries=[];baselines=[];part_metadata=[]
    with (output/'telemetry.jsonl').open('w') as telemetry, (output/'failures.jsonl').open('w') as failures:
        for index,name in enumerate(protocol['instances']):
            part=output/'parts'/name
            metadata=json.loads((part/'metadata.json').read_text())
            if metadata['failures'] or (part/'failures.jsonl').read_text():
                raise ValueError('partition has recorded failures: '+name)
            part_metadata.append(metadata)
            def remap(record):
                record['input_index']=index
                if 'run_id' in record:
                    record['run_id']=str(index)+'-'+record['run_id'].split('-',1)[1]
                return record
            with (part/'runs.csv').open() as stream:
                part_rows=list(csv.DictReader(stream))
            for row in part_rows:
                original=row['run_id']
                result=remap(json.loads((part/(original+'.json')).read_text()))
                (output/(result['run_id']+'.json')).write_text(json.dumps(result,indent=2)+'\n')
                history=result['history'];sampled=history[::max(1,(len(history)+199)//200)]
                if sampled[-1] is not history[-1]: sampled.append(history[-1])
                runs.append(result | dict(history=sampled,evaluations=len(history),history_max=max(e['current'] for e in history)))
                rows.append(remap(row))
            with (part/'summary.csv').open() as stream:
                summaries.extend(remap(row) for row in csv.DictReader(stream))
            baselines.extend(remap(row) for row in json.loads((part/'baselines.json').read_text()))
            with (part/'telemetry.jsonl').open() as stream:
                for line in stream:
                    event=json.loads(line)
                    event['run_id']=str(index)+'-'+event['run_id'].split('-',1)[1]
                    telemetry.write(json.dumps(event)+'\n')
            print('Merged '+name,flush=True)
    metadata=dict(part_metadata[0])
    metadata['inputs']=[record for part in part_metadata for record in part['inputs']]
    metadata['arguments']=dict(metadata['arguments'],instances=['instances/public/'+name+'.json' for name in protocol['instances']],output=str(output))
    metadata['execution']=dict(mode='independent instance processes',workers=workers,resumed=resumed,partition_metadata=part_metadata,
                               note='Runtime includes contention between workers; do not compare isolated speed with the sequential baseline')
    write_csv(output/'runs.csv',rows);write_csv(output/'summary.csv',summaries)
    (output/'metadata.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (output/'baselines.json').write_text(json.dumps(baselines,indent=2)+'\n')
    write_report(output/'report.html',runs)
    print(f'Finished: {len(rows)} runs merged into {output}',flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--protocol',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    protocol=json.loads(args.protocol.read_text())
    if tuple(protocol['instances'])!=NAMES or protocol['parameters']!=DEFAULTS:
        parser.error('requires the verified public instances and recorded base defaults')
    overrides=protocol['parameter_overrides']
    if not isinstance(overrides,dict) or set(overrides)-set(protocol['algorithms']):
        parser.error('invalid per-algorithm overrides')
    seeds=protocol['seeds']
    if seeds!=list(range(seeds[0],seeds[0]+len(seeds))) or args.workers<1:
        parser.error('requires consecutive seeds and positive worker count')
    args.output.mkdir(parents=True,exist_ok=args.resume)
    (args.output/'parts').mkdir(exist_ok=args.resume)
    parameters=args.output/'parameters.json'
    if parameters.exists() and json.loads(parameters.read_text())!=overrides:
        parser.error('parameter overrides differ from the saved campaign')
    parameters.write_text(json.dumps(overrides,indent=2)+'\n')
    def run(name):
        target=args.output/'parts'/name
        if args.resume and (target/'metadata.json').exists():
            previous=json.loads((target/'metadata.json').read_text())
            requested=(protocol['budget'],len(seeds),seeds[0],protocol['algorithms'])
            actual=tuple(previous['arguments'][key] for key in ('budget','repeats','seed','algorithms'))
            if previous['failures']==0 and actual==requested and previous['parameter_overrides']==overrides: return name
        command=[sys.executable,'-m','jssp','--instances','instances/public/'+name+'.json',
                 '--algorithms',*protocol['algorithms'],'--budget',str(protocol['budget']),
                 '--repeats',str(len(seeds)),'--seed',str(seeds[0]),'--quiet','--parameters',str(parameters),'--output',str(target)]
        if args.resume and target.exists(): command.append('--resume')
        with (args.output/'parts'/(name+'.log')).open('a') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
        return name
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        order=sorted(protocol['instances'],key=lambda name:len(load(ROOT/'instances/public'/(name+'.json')).sequence),reverse=True)
        jobs=[pool.submit(run,name) for name in order]
        for done,job in enumerate(as_completed(jobs),1):
            print(f'Completed instance {job.result()} ({done}/{len(jobs)})',flush=True)
    merge(args.output,protocol,args.workers,args.resume)


if __name__=='__main__': main()
