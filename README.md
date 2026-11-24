# Job-shop scheduling with four metaheuristics

Compare Genetic Algorithm (GA), Discrete Particle Swarm Optimization (DPSO), Ant Colony Optimization (ACO) and Simulated Annealing (SA) on the same scheduling problem. Each method searches for a smaller **makespan**: the time when all jobs finish.

## Run

Python 3.9+ is sufficient for the scheduler; no extra packages are required. From the repository root:

```sh
python3 -m jssp --instances instances/crossed.json --budget 1000 --repeats 2 --output results/demo
python3 -m unittest discover -s tests -v
```

The terminal shows progress. Open the generated `report.html` for live convergence curves and machine Gantt charts. The report refreshes during execution and becomes static when finished. Choose a new output directory for each campaign.

Use `--algorithms ga dpso aco sa`, `--budget`, `--repeats`, `--seed` and `--parameters path/to/parameters.json` to control a run. Defaults are all four algorithms, 1,000 evaluations and 20 seeds starting at zero. Parameters selected by pilot tuning are applied by the recorded tuned protocol, not by changing the program defaults.

## Scheduling model

Job $j$ contains ordered operations $O_{j,k}$, each with fixed machine $m_{j,k}$ and duration $d_{j,k}$. Operations cannot be interrupted; all jobs are available at time zero. There are no setup times, deadlines or alternative machines.

$$
\min C_{\max}=\max_{j,k} C_{j,k},\qquad
C_{j,k}=S_{j,k}+d_{j,k},\qquad
S_{j,k+1}\ge C_{j,k}.
$$

Operations $a,b$ sharing a machine must satisfy $C_a\le S_b$ or $C_b\le S_a$, with all start times nonnegative.

A candidate $x$ is a job priority list: job $j$ appears once per operation. For example, $[0,1,0,1]$ selects each job's first operation, then its second. The **decoder** inserts each selected operation into the earliest machine gap after its job predecessor finishes. Independent operations can run together. A shared validator checks coverage, machines, durations, precedence and overlap.

All methods use this representation, decoder and objective $C(x)=C_{\max}$. Each receives exactly $B$ candidate evaluations, counting initialization, duplicates and rejected neighbors. Equal evaluations do not mean equal runtime. A separate Shortest Processing Time (SPT) baseline provides a simple reference schedule.

## Approaches

| Method | Search idea | Explanation |
| --- | --- | --- |
| GA | Select parents using $f(x)=1/C(x)$; preserve job counts through crossover and swaps; retain an elite. | [Chromosomes, selection and crossover](docs/ga/README.md) |
| DPSO | Apply sampled swap lists toward personal and swarm bests. | [Positions, velocity and memory](docs/dpso/README.md) |
| ACO | Build lists with weights $\tau^\alpha(1/d)^\beta$; evaporate and reinforce transitions. | [Choices and pheromone updates](docs/aco/README.md) |
| SA | Swap neighbors; accept a worsening $\Delta>0$ with probability $e^{-\Delta/T}$; cool $T$. | [Acceptance and cooling](docs/sa/README.md) |

## Results

The study uses 18 public benchmark instances and 20 seeds per algorithm: 1,440 runs per campaign. Input data and reference values were cross-checked; the [verification manifest](benchmarks/manifest.json) retains the data provenance. Small hand-checkable cases and larger synthetic cases also exercise the implementation.

Quality is measured against each instance's best-known solution (BKS):

$$
\mathrm{RPD}=100\frac{C_{\max}-\mathrm{BKS}}{\mathrm{BKS}}.
$$

Lower is better. Values below average RPD equally across the 18 instances, using all 20 seeds per instance.

| Algorithm | Default, 1,000 evaluations | Default, 10,000 evaluations | Pilot-selected, 10,000 evaluations |
| --- | ---: | ---: | ---: |
| GA | 8.60% | 5.4768% | 5.4768% |
| DPSO | 9.18% | 6.7817% | 5.6277% |
| ACO | 16.61% | 15.6841% | 15.3070% |
| SA | 6.88% | 3.6189% | 3.3629% |

Tuning tested four configurations per algorithm on four separate pilot instances with three seeds each. Selection used pilot mean RPD, then froze one configuration per algorithm for the final run. GA retained its defaults. Tuning added 1.92 million evaluations; each 10,000-evaluation final campaign used 14.4 million. All final runs passed the schedule and history audits.

Statistical tests use **18 instance means**, each averaging 20 seeds. Friedman finds an overall difference in the tuned campaign (99,999-permutation check, $p=0.000010$ at its sampling resolution). Exact paired Wilcoxon tests with Holm correction separate five of six algorithm pairs: SA has lower RPD than the others, ACO has higher RPD, and GA versus DPSO is not significantly separated ($p=0.80395508$). All six pairs were significant in both default campaigns.

DPSO's tuning improvement is significant after correcting the four tuning-change tests ($p=0.00048828$). ACO and SA improve their aggregate means without a significant corrected tuning change; GA is unchanged. A nonsignificant test does not prove equality. These findings describe this sample and these implementations; earlier benchmark outcomes were already known before the pilot follow-up.

| Evidence | Location |
| --- | --- |
| Original 1,000-evaluation campaign | [Results and statistics](experiments/public-18) |
| Default 10,000-evaluation campaign | [Results and budget comparison](experiments/public-18-10000) |
| Pilot candidates and selection | [Tuning records](experiments/pilot-tuning) |
| Selected 10,000-evaluation campaign | [Results, audit and statistical comparisons](experiments/public-18-tuned) |

## Output and reproduction

Every campaign writes `telemetry.jsonl` during execution, full histories and validated schedules in per-run JSON, `runs.csv`, `summary.csv`, input/settings metadata, failure records and `report.html`. Curves display sampled points; full histories remain in the run files. Raw output stays local under ignored `results/`; compact experiment evidence is versioned.

Repeat the selected campaign into a new directory:

```sh
python3 scripts/run_partitioned_experiment.py --protocol experiments/public-18-tuned/protocol.json --output results/tuned-rerun --workers 4
python3 scripts/audit_public_results.py results/tuned-rerun results/tuned-rerun-evidence
```

Add `--resume` to the runner after an interruption. For statistical analysis, install the pinned dependencies using `uv`:

```sh
uv run --python 3.14 --with-requirements requirements-statistics.txt python scripts/analyze_public_results.py experiments/public-18-tuned
```

For the complete tuning and comparison commands, see [experiment reproduction](docs/experiments.md). Reproduction depends on the recorded inputs, settings, seeds and software versions; observed runtimes vary.
