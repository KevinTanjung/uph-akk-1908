import csv
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from scripts.audit_public_results import audit

ROOT=Path(__file__).resolve().parents[1]

class PartitionTests(unittest.TestCase):
    def test_parallel_run_merge_and_audit(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'evidence';target.mkdir()
            protocol=json.loads((ROOT/'experiments/public-18/protocol.json').read_text())
            protocol.update(budget=3,seeds=[0,1])
            path=target/'protocol.json';path.write_text(json.dumps(protocol))
            output=root/'raw'
            subprocess.run([sys.executable,str(ROOT/'scripts/run_partitioned_experiment.py'),
                            '--protocol',str(path),'--output',str(output),'--workers','2'],
                           cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
            # Simulate a worker interrupted after writing all but its last run file.
            part=output/'parts/la36'
            (part/'metadata.json').unlink()
            (part/'0-sa-1.json').unlink()
            subprocess.run([sys.executable,str(ROOT/'scripts/run_partitioned_experiment.py'),
                            '--protocol',str(path),'--output',str(output),'--workers','2','--resume'],
                           cwd=ROOT,stdout=subprocess.DEVNULL,check=True)
            recovered=json.loads((part/'metadata.json').read_text())['recovered_run_ids']
            self.assertEqual(len(recovered),7)
            self.assertNotIn('0-sa-1',recovered)
            audit(output,target)
            with (output/'runs.csv').open() as stream: rows=list(csv.DictReader(stream))
            self.assertEqual(len(rows),144)
            self.assertEqual(len({row['run_id'] for row in rows}),144)
            self.assertEqual(json.loads((target/'audit.json').read_text())['candidate_evaluations'],432)
            self.assertEqual(json.loads((output/'metadata.json').read_text())['execution']['workers'],2)

if __name__=='__main__': unittest.main()
