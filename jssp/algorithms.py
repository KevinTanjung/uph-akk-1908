"""Scheduling adaptations of the mechanisms in the supplied materials."""
import math
import random
from time import perf_counter
from .core import decode, validate

DEFAULTS = dict(population=20, crossover=0.8, mutation=0.2, inertia=0.5,
                cognitive=0.5, social=0.5, alpha=1., beta=2., evaporation=0.1,
                deposit=1., temperature=20., cooling=0.995)


def neighbor(seq, rng):
    child = seq[:]
    if len(child) > 1:
        a,b = rng.sample(range(len(child)),2)
        child[a],child[b] = child[b],child[a]
    return child


def crossover(a,b,rng):
    selected = {j for j in set(a) if rng.random() < .5}
    remaining = iter(j for j in b if j not in selected)
    return [j if j in selected else next(remaining) for j in a]


def difference(current,target):
    work = current[:]
    swaps = []
    for i,value in enumerate(target):
        if work[i] != value:
            k = work.index(value,i+1)
            swaps.append((i,k));work[i],work[k] = work[k],work[i]
    return swaps


def solve(instance, algorithm, budget=1000, seed=0, callback=None, **overrides):
    if algorithm not in ('ga','dpso','aco','sa') or type(budget) is not int or budget < 1:
        raise ValueError('known algorithm and positive integer budget required')
    if set(overrides)-DEFAULTS.keys(): raise ValueError('unknown parameter')
    cfg = DEFAULTS | overrides
    if type(cfg['population']) is not int or cfg['population'] < 2: raise ValueError('population >= 2 required')
    for key,value in cfg.items():
        if not isinstance(value,(int,float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('parameters must be positive and finite')
    for key in ('crossover','mutation','inertia','cognitive','social','evaporation','cooling'):
        if cfg[key] > 1 or (key in ('evaporation','cooling') and cfg[key] == 1):
            raise ValueError('invalid probability or rate')
    base_sequence = instance.sequence
    operation_count = len(base_sequence)
    rng = random.Random(seed)
    history=[];best=None;best_score=math.inf;start=perf_counter()
    def evaluate(seq):
        nonlocal best,best_score
        score,_ = decode(instance,seq)
        if score < best_score: best,best_score = seq[:],score
        event=dict(evaluation=len(history)+1,current=score,best=best_score,elapsed_seconds=perf_counter()-start)
        history.append(event)
        if callback: callback(event | dict(best_sequence=best[:]))
        return score
    def shuffled():
        seq=base_sequence[:];rng.shuffle(seq);return seq
    size=min(cfg['population'],budget)
    if algorithm in ('ga','dpso'):
        pop=[shuffled() for _ in range(size)];scores=[evaluate(s) for s in pop]
        personal=[s[:] for s in pop];personal_scores=scores[:];velocities=[[] for _ in pop]
    elif algorithm == 'sa':
        current=shuffled();score=evaluate(current);temperature=cfg['temperature']
    else:
        ops=[(j,k) for j,job in enumerate(instance.jobs) for k in range(len(job))]
        pheromone={(a,b):1. for a in [None]+ops for b in ops}
        heuristic={op:(1/instance.jobs[op[0]][op[1]][1])**cfg['beta'] for op in ops}
    while len(history) < budget:
        if algorithm == 'ga':
            elite=min(range(len(pop)),key=lambda i:scores[i])
            new,new_scores=[pop[elite][:]],[scores[elite]]
            while len(new)<size and len(history)<budget:
                a,b=rng.choices(pop,weights=[1/s for s in scores],k=2)
                child=crossover(a,b,rng) if rng.random()<cfg['crossover'] else a[:]
                if rng.random()<cfg['mutation']: child=neighbor(child,rng)
                new.append(child);new_scores.append(evaluate(child))
            pop,scores=new,new_scores
        elif algorithm == 'dpso':
            leader=best[:]
            for i in range(size):
                if len(history)==budget: break
                swaps=[s for s in velocities[i] if rng.random()<cfg['inertia']]
                swaps += [s for s in difference(pop[i],personal[i]) if rng.random()<cfg['cognitive']]
                swaps += [s for s in difference(pop[i],leader) if rng.random()<cfg['social']]
                swaps=swaps[:2*operation_count]
                child=pop[i][:]
                for a,b in swaps: child[a],child[b]=child[b],child[a]
                if rng.random()<cfg['mutation']: child=neighbor(child,rng)
                velocities[i]=swaps;pop[i]=child;score=evaluate(child)
                if score<personal_scores[i]: personal[i],personal_scores[i]=child[:],score
        elif algorithm == 'aco':
            colony=[]
            for _ in range(min(size,budget-len(history))):
                seq=[];edges=[];counts=[0]*len(instance.jobs);previous=None
                while len(seq)<operation_count:
                    eligible=[(j,counts[j]) for j,job in enumerate(instance.jobs) if counts[j]<len(job)]
                    weights=[pheromone[previous,op]**cfg['alpha']*heuristic[op] for op in eligible]
                    op=rng.choices(eligible,weights=weights)[0]
                    edges.append((previous,op));seq.append(op[0]);counts[op[0]]+=1;previous=op
                colony.append((edges,evaluate(seq)))
            for edge in pheromone: pheromone[edge]=max(1e-12,pheromone[edge]*(1-cfg['evaporation']))
            for edges,score in colony:
                for edge in edges: pheromone[edge]+=cfg['deposit']/score
        else:
            child=neighbor(current,rng);candidate=evaluate(child);delta=candidate-score
            if delta<=0 or rng.random()<math.exp(-delta/max(temperature,1e-12)): current,score=child,candidate
            temperature=max(1e-12,temperature*cfg['cooling'])
    makespan,schedule=decode(instance,best);validate(instance,schedule)
    return dict(algorithm=algorithm,seed=seed,budget=budget,parameters=cfg,makespan=makespan,
                sequence=best,schedule=schedule,history=history,runtime_seconds=perf_counter()-start,
                rpd=None if instance.bks is None else 100*(makespan-instance.bks)/instance.bks)
