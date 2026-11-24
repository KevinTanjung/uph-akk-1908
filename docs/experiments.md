# Reproduce the experiments

Run commands from the repository root. Use a fresh output directory to preserve existing evidence. The frozen protocols contain instance lists, seeds, budgets and effective settings. The statistical tools require the pinned packages in `requirements-statistics.txt`; the scheduler itself uses the Python standard library.

## Default campaigns

```sh
python3 -m jssp --instances instances/public/*.json --algorithms ga dpso aco sa --budget 1000 --repeats 20 --seed 0 --quiet --output results/public-18-1000-rerun
python3 scripts/audit_public_results.py results/public-18-1000-rerun results/public-18-1000-rerun-evidence
python3 scripts/run_partitioned_experiment.py --protocol experiments/public-18-10000/protocol.json --output results/public-18-10000-rerun --workers 4
python3 scripts/audit_public_results.py results/public-18-10000-rerun results/public-18-10000-rerun-evidence
```

## Pilot selection and selected settings

The recorded search evaluated four configurations per algorithm on LA03, LA13, LA23 and LA37, using seeds 100-102 and 10,000 evaluations per trial. Selection minimized mean RPD across the 12 pilot runs, retaining the lower configuration index on a tie. Final benchmarks use different instances and seeds 0-19.

```sh
python3 scripts/tune_pilots.py --output results/pilot-tuning-rerun --workers 4
python3 scripts/run_partitioned_experiment.py --protocol experiments/public-18-tuned/protocol.json --output results/public-18-tuned-rerun --workers 4
python3 scripts/audit_public_results.py results/public-18-tuned-rerun results/public-18-tuned-rerun-evidence
```

The final command uses the already frozen selection in the protocol. If a new tuning search produces different choices, freeze a new protocol with those values and selection hashes before evaluating benchmarks. Do not silently replace the protocol of the reported study. Add `--resume` to an interrupted runner to validate and reuse completed runs.

## Statistical analysis

The following commands regenerate analysis of the versioned evidence:

```sh
uv run --python 3.14 --with-requirements requirements-statistics.txt python scripts/analyze_public_results.py experiments/public-18
uv run --python 3.14 --with-requirements requirements-statistics.txt python scripts/analyze_public_results.py experiments/public-18-10000
uv run --python 3.14 --with-requirements requirements-statistics.txt python scripts/analyze_public_results.py experiments/public-18-tuned
uv run --python 3.14 --with-requirements requirements-statistics.txt python scripts/compare_public_budgets.py
uv run --python 3.14 --with-requirements requirements-statistics.txt python scripts/compare_public_budgets.py --baseline experiments/public-18-10000 --candidate experiments/public-18-tuned --tuning
```

These commands write analysis files. The default budget comparison additionally checks shared search prefixes using the original full local outputs; compact versioned evidence alone does not contain every raw history. Audit a fresh campaign into a separate evidence directory before analyzing that rerun.

Friedman compares within-instance ranks, using tie correction and a 99,999-draw permutation check. Post-hoc tests use exact two-sided Wilcoxon signed-rank calculations on 18 paired mean RPD differences, with Holm correction across the six pairs. Separate four-test families cover budget changes and tuning changes. The threshold is 0.05; signed-rank tests assume symmetric paired differences under the null.

See [the overview](../README.md#results) for the conclusions and links to per-seed outcomes, audits and analysis inputs. The 18 selected instances span two benchmark families; four pilot configurations per algorithm are a limited search, and this follow-up is exploratory because earlier benchmark outcomes had already been inspected.
