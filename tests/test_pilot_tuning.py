import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from jssp.benchmarks import NAMES,verify_sources
from jssp.core import load
from scripts.tune_pilots import select,validate_plan

ROOT=Path(__file__).resolve().parents[1]

class PilotTuningTests(unittest.TestCase):
    def test_separate_verified_pilot_data(self):
        plan=json.loads((ROOT/'experiments/pilot-tuning/plan.json').read_text())
        self.assertFalse(set(plan['instances'])&set(NAMES))
        instances,_=verify_sources(names=plan['instances'])
        final={load(ROOT/'instances/public'/(name+'.json')).jobs for name in NAMES}
        for inst in instances:
            pilot=load(ROOT/'instances/pilot'/(inst.name+'.json'))
            self.assertEqual((pilot.jobs,pilot.bks),(inst.jobs,inst.bks))
            self.assertNotIn(pilot.jobs,final)

    def test_selector_uses_all_trials_and_prefers_defaults_on_ties(self):
        plan=json.loads((ROOT/'experiments/pilot-tuning/plan.json').read_text())
        plan.update(instances=['la03'],seeds=[100],budget=5)
        plan['configurations']={alg:cfg[:2] for alg,cfg in plan['configurations'].items()}
        trials=[dict(algorithm=alg,configuration=cfg,instance='la03',seed=100,makespan=110-10*cfg,bks=100,evaluations=5)
                for alg in plan['algorithms'] for cfg in range(2)]
        _,chosen,_=select(trials,plan)
        self.assertTrue(all(index==1 for index in chosen.values()))
        for row in trials:row['makespan']=110
        _,chosen,_=select(trials,plan)
        self.assertTrue(all(index==0 for index in chosen.values()))
        with self.assertRaisesRegex(ValueError,'missing'):select(trials[:-1],plan)
        leaked=copy.deepcopy(plan);leaked['instances']=[NAMES[0]]
        with self.assertRaisesRegex(ValueError,'overlap'):validate_plan(leaked)
        leaked=copy.deepcopy(plan);leaked['seeds']=[0]
        with self.assertRaisesRegex(ValueError,'seeds overlap'):validate_plan(leaked)

    def test_small_complete_tuning_campaign(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan=json.loads((ROOT/'experiments/pilot-tuning/plan.json').read_text())
            plan.update(budget=3,seeds=[100,101])
            plan['configurations']={alg:cfg[:2] for alg,cfg in plan['configurations'].items()}
            path=root/'plan.json';path.write_text(json.dumps(plan));target=root/'evidence'
            subprocess.run([sys.executable,str(ROOT/'scripts/tune_pilots.py'),'--plan',str(path),
                            '--output',str(root/'raw'),'--evidence',str(target),'--workers','2'],
                           cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
            result=json.loads((target/'selection.json').read_text())
            self.assertEqual(result['trials'],64)
            self.assertEqual(result['candidate_evaluations'],192)
            self.assertEqual(result['failures'],0)
            for alg in plan['algorithms']:
                group=[r for r in result['scores'] if r['algorithm']==alg]
                self.assertLessEqual(next(r['mean_rpd'] for r in group if r['selected']),group[0]['mean_rpd'])

if __name__=='__main__': unittest.main()
