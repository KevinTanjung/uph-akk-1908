import itertools
import random
import tempfile
import unittest
from pathlib import Path
from jssp.core import Instance,decode,load,load_orlib,spt,validate
from jssp.algorithms import solve,crossover,difference
ROOT=Path(__file__).resolve().parents[1]
class Tests(unittest.TestCase):
    def test_optima(self):
        for name in ('single','bottleneck','crossed','unequal'):
            inst=load(ROOT/'instances'/f'{name}.json');scores=[]
            for seq in set(itertools.permutations(inst.sequence)):
                score,ops=decode(inst,seq);validate(inst,ops);scores.append(score)
            self.assertEqual(min(scores),inst.bks)
    def test_algorithms(self):
        for path in sorted((ROOT/'instances').glob('*.json')):
            inst=load(path);validate(inst,decode(inst,spt(inst))[1])
            for alg in ('ga','dpso','aco','sa'):
                for budget in (1,7,43):
                    with self.subTest(case=inst.name,algorithm=alg,budget=budget):
                        r=solve(inst,alg,budget,42);other=solve(inst,alg,budget,42)
                        self.assertEqual(r['sequence'],other['sequence'])
                        self.assertEqual(len(r['history']),budget)
                        validate(inst,r['schedule'])
                        best=[x['best'] for x in r['history']]
                        self.assertEqual(best,sorted(best,reverse=True))
                        self.assertEqual(r['makespan'],best[-1])
                        self.assertGreaterEqual(r['makespan'],inst.lower_bound)
    def test_operators(self):
        a,b=[0,0,1,1,2],[1,0,2,1,0];rng=random.Random(1)
        for _ in range(100): self.assertEqual(sorted(crossover(a,b,rng)),sorted(a))
        for i,j in difference(a,b): a[i],a[j]=a[j],a[i]
        self.assertEqual(a,b)
    def test_gap(self):
        score,ops=decode(load(ROOT/'instances/idle_gap.json'),[0,0,1,1])
        self.assertEqual(ops[2]['start'],0);self.assertEqual(score,5)
    def test_invalid(self):
        for jobs in ((),((),),(((0,0),),),(((2,1),),)):
            with self.assertRaises(ValueError): Instance('bad',1,jobs)
        inst=load(ROOT/'instances/crossed.json')
        with self.assertRaises(ValueError): decode(inst,[0,1])
        _,ops=decode(inst,inst.sequence)
        with self.assertRaises(ValueError): validate(inst,ops[:-1])
        ops[1]['start']=0;ops[1]['end']=2
        with self.assertRaises(ValueError): validate(inst,ops)
        for kw in ({'budget':0},{'cooling':1},{'population':1},{'temperature':float('nan')}):
            with self.assertRaises(ValueError): solve(inst,'ga',**kw)
    def test_orlib(self):
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'jobshop1';path.write_text('instance demo\n++++\ndescription\n2 2\n0 3 1 2\n1 3 0 2\n')
            self.assertEqual(decode(load_orlib(path,'demo'),[0,1,0,1])[0],5)
            with self.assertRaises(ValueError): load_orlib(path,'missing')
if __name__=='__main__': unittest.main()
