"""Optional SciPy tests; core scheduling tests still run without analysis packages."""
import contextlib
import io
import hashlib
import importlib.util
import json
import math
import os
import shutil
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

AVAILABLE = importlib.util.find_spec('scipy') is not None
if AVAILABLE:
    import numpy as np
    from scipy import stats
    from scripts.compare_public_budgets import check_prefixes,compare
    from scripts.analyze_public_results import EXPERIMENT, friedman, holm, load_blocks, paired_test


@unittest.skipUnless(AVAILABLE, 'optional SciPy analysis dependencies are not installed')
class StatisticsTests(unittest.TestCase):
    def test_holm_known_values_and_original_order(self):
        self.assertEqual(holm([.04,.01,.03]), [.06,.03,.06])
        self.assertEqual(holm([1.,1.]), [1.,1.])

    def test_exact_wilcoxon_ties_zeros_and_mixed_signs(self):
        result = paired_test([0,1,1,1])
        self.assertEqual(result['pvalue'], .25)
        self.assertEqual(result['nonzero_pairs'], 3)
        self.assertEqual(result['sign_assignments'], 8)
        self.assertEqual(paired_test([1,-2,3,-4])['pvalue'], .875)
        self.assertEqual(paired_test([0,0,0])['pvalue'], 1.)
        for differences in ([1,1,-2,3], [1,-2,3,-4], [1,2,3,4,5]):
            reference = stats.wilcoxon(differences, method=stats.PermutationMethod(n_resamples=np.inf))
            actual = paired_test(differences)
            self.assertEqual(actual['statistic'], reference.statistic)
            self.assertEqual(actual['pvalue'], reference.pvalue)

    def test_friedman_perfect_order_and_tie_correction(self):
        for row in ([1,2,3,4], [1,1,3,4]):
            result, ranks = friedman(np.tile(row,(10,1)), permutations=99, seed=4)
            self.assertAlmostEqual(result['statistic'],30.)
            self.assertAlmostEqual(result['kendalls_w'],1.)
            self.assertEqual(result['exceedances'],0)
            self.assertEqual(result['permutation_pvalue'],.01)
        with self.assertRaises(ValueError): friedman(np.ones((10,4)))

    def test_budget_comparison_rejects_changed_search_prefix(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            old=dict(instance='case',algorithm='ga',seed=0,parameters={},budget=2,makespan=8,
                     history=[dict(current=10,best=10),dict(current=8,best=8)])
            new=dict(old,budget=3,makespan=7,history=old['history']+[dict(current=7,best=7)])
            for label,record in [('old',old),('new',new)]:
                target=root/label;target.mkdir();raw=root/(label+'-raw');raw.mkdir()
                path=raw/'0-ga-0.json';path.write_text(json.dumps(record))
                (target/'audit.json').write_text(json.dumps(dict(raw_output_directory=str(raw),evaluations_per_run=record['budget'],
                    raw_sha256={path.name:hashlib.sha256(path.read_bytes()).hexdigest()})))
            (root/'old/runs.csv').write_text('run_id\n0-ga-0\n')
            self.assertEqual(check_prefixes(root/'old',root/'new')['matched_candidate_evaluations'],2)
            new['history'][0]=dict(current=11,best=11)
            path=root/'new-raw/0-ga-0.json';path.write_text(json.dumps(new))
            audit=json.loads((root/'new/audit.json').read_text())
            audit['raw_sha256'][path.name]=hashlib.sha256(path.read_bytes()).hexdigest()
            (root/'new/audit.json').write_text(json.dumps(audit))
            with self.assertRaisesRegex(ValueError,'search prefix differs'):
                check_prefixes(root/'old',root/'new')

    def test_tuning_comparison_accepts_equal_budgets_and_changed_parameters(self):
        source=EXPERIMENT.parent/'public-18-10000'
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder).resolve();old=root/'baseline';new=root/'candidate'
            for target in (old,new):
                target.mkdir()
                for name in ('protocol.json','runs.csv','metadata.json','audit.json','statistics.json'):
                    shutil.copyfile(source/name,target/name)
            protocol=json.loads((new/'protocol.json').read_text())
            protocol['parameter_overrides']={'sa':{'temperature':30.0}}
            (new/'protocol.json').write_text(json.dumps(protocol))
            metadata=json.loads((new/'metadata.json').read_text())
            metadata['parameter_overrides']=protocol['parameter_overrides']
            (new/'metadata.json').write_text(json.dumps(metadata))
            audit=json.loads((new/'audit.json').read_text())
            audit['raw_sha256']['metadata.json']=hashlib.sha256((new/'metadata.json').read_bytes()).hexdigest()
            (new/'audit.json').write_text(json.dumps(audit))
            stats_record=json.loads((new/'statistics.json').read_text())
            stats_record['input_sha256']={name:hashlib.sha256((new/name).read_bytes()).hexdigest()
                                          for name in stats_record['input_sha256']}
            (new/'statistics.json').write_text(json.dumps(stats_record))
            previous=Path.cwd()
            try:
                os.chdir(root)
                with patch('scripts.compare_public_budgets.ROOT',root),contextlib.redirect_stdout(io.StringIO()):
                    compare(Path('baseline'),Path('candidate'),tuning=True)
            finally:
                os.chdir(previous)
            result=json.loads((new/'tuning-comparison.json').read_text())
            self.assertEqual(result['baseline_budget'],result['candidate_budget'])
            self.assertTrue(all(row['pvalue']==1 and not row['significant_at_0_05'] for row in result['improvements']))
            self.assertIn('Not applicable',result['prefix_verification']['status'])
            self.assertEqual(result['unchanged_settings_controls']['ga']['matched_runs'],360)
            self.assertNotIn('sa',result['unchanged_settings_controls'])
            self.assertFalse((new/'budget-comparison.json').exists())

    def test_audited_18_blocks_and_checksum_protection(self):
        protocol, totals, rpds = load_blocks()
        self.assertEqual(totals.shape,(18,4))
        self.assertEqual(len(protocol['seeds']),20)
        self.assertTrue(math.isclose(float(rpds[0][0]), 100*(56.55-55)/55))
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            for name in ('protocol.json','runs.csv','audit.json','metadata.json'):
                shutil.copyfile(EXPERIMENT/name,target/name)
            path=target/'runs.csv'
            path.write_bytes(path.read_bytes()+b'\n')
            with self.assertRaisesRegex(ValueError,'no longer matches'): load_blocks(target)
            lines=path.read_bytes().splitlines(keepends=True)
            path.write_bytes(b''.join(lines[:-2]))
            audit=json.loads((target/'audit.json').read_text())
            audit['raw_sha256']['runs.csv']=hashlib.sha256(path.read_bytes()).hexdigest()
            (target/'audit.json').write_text(json.dumps(audit))
            with self.assertRaisesRegex(ValueError,'incomplete'): load_blocks(target)


if __name__ == '__main__': unittest.main()
