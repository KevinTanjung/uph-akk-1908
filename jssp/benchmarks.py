"""Verify the stored public sources and rebuild the 18 experiment inputs."""
import hashlib
import json
from dataclasses import replace, asdict
from pathlib import Path
from .core import load_orlib

ROOT = Path(__file__).resolve().parents[1]
NAMES = ('ft06','ft10','ft20','la01','la02','la06','la07','la11','la12',
         'la16','la17','la21','la22','la26','la27','la31','la32','la36')
JSPLIB = 'eea2b60dd7e2f5c907ff7302662c61812eb7efdf'
SCHEDULEOPT = '824cf4d53117c6d64bb952c337ff73eacb363a5f'
URLS = {
    'jobshop1.txt': 'https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/jobshop1.txt',
    'jsplib/instances.json': f'https://raw.githubusercontent.com/tamy0612/JSPLIB/{JSPLIB}/instances.json',
    'scheduleopt-bks.json': f'https://raw.githubusercontent.com/ScheduleOpt/benchmarks/{SCHEDULEOPT}/jobshop/solutions/bks.json',
}


def verify_sources(folder=ROOT/'benchmarks/sources', names=NAMES):
    folder = Path(folder)
    primary = {row['name']: row for row in json.loads((folder/'jsplib/instances.json').read_text())}
    secondary = {row['instance']: row for row in json.loads((folder/'scheduleopt-bks.json').read_text())}
    records, instances = [], []
    for name in names:
        inst = load_orlib(folder/'jobshop1.txt', name)
        lines = [line.strip() for line in (folder/'jsplib'/name).read_text().splitlines()
                 if line.strip() and not line.lstrip().startswith('#')]
        n, m = map(int, lines[0].split())
        rows = [list(map(int, line.split())) for line in lines[1:]]
        if len(rows) != n or any(len(row) != 2*m for row in rows):
            raise ValueError('invalid JSPLIB data: '+name)
        jobs = tuple(tuple(zip(row[::2],row[1::2])) for row in rows)
        a, b = primary[name], secondary[name]
        if (n,m) != (len(inst.jobs),inst.machines) or jobs != inst.jobs:
            raise ValueError('OR-Library / JSPLIB data disagreement: '+name)
        if (n,m) != (a['jobs'],a['machines']) or b['size'].replace(' ','') != f'{n}x{m}':
            raise ValueError('catalogue dimensions disagree: '+name)
        if any(len(job) != m or {machine for machine,_ in job} != set(range(m)) for job in jobs):
            raise ValueError('not a classical full-route instance: '+name)
        bks = a['optimum']
        if b['lower_bound'] != bks or b['upper_bound'] != bks or b['status'] != 'closed':
            raise ValueError('BKS sources disagree or optimum not established: '+name)
        inst = replace(inst,bks=bks,source=f"OR-Library jobshop1; operation data checked against JSPLIB {JSPLIB}; BKS {bks} matches JSPLIB optimum and ScheduleOpt {SCHEDULEOPT} closed lower/upper bounds; see benchmarks/manifest.json")
        if inst.lower_bound > bks: raise ValueError('BKS below elementary lower bound: '+name)
        instances.append(inst)
        records.append(dict(name=name,jobs=n,machines=m,bks=bks,status='optimum reported by both catalogues',
                            jsplib=a,scheduleopt=b))
    urls = URLS | {f'jsplib/{name}':f'https://raw.githubusercontent.com/tamy0612/JSPLIB/{JSPLIB}/instances/{name}' for name in names}
    sources = {name:dict(url=url,sha256=hashlib.sha256((folder/name).read_bytes()).hexdigest()) for name,url in urls.items()}
    return instances, dict(verified_date='2026-11-21',sources=sources,instances=records,
                           checks=['All operation pairs agree between OR-Library and JSPLIB',
                                   'Dimensions and classical full-machine routes checked',
                                   'BKS equals JSPLIB optimum and both ScheduleOpt bounds; status closed',
                                   'BKS is at least the elementary job/machine workload lower bound'],
                           limitation='Catalogue agreement was checked; mathematical optimality proofs were not reproduced.')


def main():
    instances,manifest = verify_sources()
    target=ROOT/'instances/public';target.mkdir(parents=True,exist_ok=True)
    for inst in instances:
        (target/(inst.name+'.json')).write_text(json.dumps(asdict(inst),indent=2)+'\n')
    (ROOT/'benchmarks/manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print(f'Verified and rebuilt {len(instances)} public instances')

if __name__=='__main__': main()
