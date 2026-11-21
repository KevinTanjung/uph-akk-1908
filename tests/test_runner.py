import json
import tempfile
import unittest
from pathlib import Path
from jssp.__main__ import main

class RunnerTests(unittest.TestCase):
    def test_outputs_and_failure_records(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);case=root/'case.json'
            case.write_text(json.dumps(dict(name='<case>',machines=1,jobs=[[[0,2]]],bks=2)))
            output=root/'run'
            self.assertEqual(main(['--instances',str(case),'--budget','3','--repeats','2','--quiet','--output',str(output)]),0)
            events=[json.loads(s) for s in (output/'telemetry.jsonl').read_text().splitlines()]
            self.assertEqual(len(events),24)
            self.assertEqual(len({e['run_id'] for e in events}),8)
            self.assertIn('&lt;case&gt;', (output/'report.html').read_text())
            self.assertNotIn('http-equiv="refresh"',(output/'report.html').read_text())
            self.assertEqual(json.loads((output/'metadata.json').read_text())['failures'],0)
            self.assertEqual((output/'failures.jsonl').read_text(),'')
            self.assertEqual(len((output/'summary.csv').read_text().splitlines()),5)
            with self.assertRaises(FileExistsError): main(['--output',str(output)])
            bad=root/'bad'
            self.assertEqual(main(['--instances',str(root/'absent'),'--quiet','--output',str(bad)]),1)
            self.assertIn('absent',(bad/'failures.jsonl').read_text())

if __name__=='__main__': unittest.main()
