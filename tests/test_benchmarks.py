import json
import shutil
import tempfile
import unittest
from pathlib import Path
from jssp.benchmarks import ROOT,NAMES,verify_sources
from jssp.core import load

class BenchmarkTests(unittest.TestCase):
    def test_sources_and_generated_instances_agree(self):
        instances,manifest=verify_sources()
        self.assertEqual(len(instances),18)
        self.assertEqual(manifest,json.loads((ROOT/'benchmarks/manifest.json').read_text()))
        for inst in instances:
            self.assertEqual(inst,load(ROOT/'instances/public'/(inst.name+'.json')))
            self.assertGreaterEqual(inst.bks,inst.lower_bound)
        self.assertEqual({i.name for i in instances},set(NAMES))

    def test_bks_disagreement_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            sources=Path(folder)/'sources'
            shutil.copytree(ROOT/'benchmarks/sources',sources)
            path=sources/'scheduleopt-bks.json';data=json.loads(path.read_text())
            next(row for row in data if row['instance']=='ft06')['upper_bound']=56
            path.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'BKS sources disagree'):
                verify_sources(sources)

if __name__=='__main__': unittest.main()
