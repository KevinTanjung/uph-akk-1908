# Comparing four ways to schedule jobs

This project follows `Proposal_UTS_KK_JSSP_Komparasi_4_Metaheuristik.pdf`, especially sections III and IV. It schedules jobs on fixed machines and tries to finish every job as early as possible. The time the last job finishes is the **makespan**. Smaller is better.

Each job has a fixed order of operations. One machine can run only one operation at a time. An operation cannot be interrupted. All jobs are available at time zero. There are no deadlines, machine choices or setup times.

## Run it

Use Python 3.9 or newer. No packages need to be installed. Run these commands from this repository:

```sh
python3 -m unittest discover -s tests -v
python3 -m jssp --instances instances/crossed.json --budget 1000 --repeats 2
python3 -m jssp --instances instances/*.json --budget 2000 --repeats 20
```

The script prints the report location and progress while it runs. Open `report.html` in a browser. It refreshes every two seconds during execution and shows candidate quality, best quality and the best schedule so far. The final report stops refreshing. The table includes every seed; charts show the best run for each instance and algorithm, plus the active run during execution. Charts sample at most 201 points per history to keep the report readable; full histories remain in the run JSON files. Gantt bars show when each machine works on each job; hover over a bar for exact times, or expand the schedule table. Report time units match the input, rather than assuming minutes.

Use `--output results/my-experiment` to choose a new output folder. Existing folders are refused to protect earlier results. `--quiet` hides candidate progress while keeping telemetry and the report. Full run output stays local and is ignored by Git. Compact evidence from the public benchmark experiment is committed under `experiments/public-18`.

The default is all four algorithms, 1,000 candidate evaluations each and 20 runs with seeds 0–19. Change the algorithm list with `--algorithms ga dpso aco sa`, the budget with `--budget`, and the first seed with `--seed`. Reusing an input, algorithm, parameters, seed and Python version reproduces the schedule; runtime measurements vary. Every candidate evaluation counts, including initialization and repeated candidates. Keeping an already evaluated GA elite does not spend another evaluation. The final validation decodes the selected answer again without adding a search evaluation.

## Read each approach

- [Genetic Algorithm: chromosome, selection, crossover and mutation](docs/ga/README.md)
- [Discrete Particle Swarm Optimization: positions, swaps and best experience](docs/dpso/README.md)
- [Ant Colony Optimization: choices, pheromone and evaporation](docs/aco/README.md)
- [Simulated Annealing: neighbors, acceptance and cooling](docs/sa/README.md)
- [Materials, exact source references and adaptation decisions](docs/materials.md)

## Shared schedule design

A candidate is a list of job numbers. Job numbers start at zero. A job appears once for each of its operations. For example, `[0, 1, 0, 1]` means job 0's first operation, job 1's first operation, job 0's second operation, then job 1's second operation. It does not mean those operations must execute one after another in time.

The **decoder** turns that priority list into a schedule. Each operation starts after the previous operation of its job and fits into the earliest open gap on its required machine. This lets unrelated operations run together. The shared **validator** checks that every operation appears exactly once, has its required machine and duration, follows its job order and does not overlap another operation on its machine.

All four algorithms use this decoder and minimize the same makespan. An SPT baseline repeatedly chooses the shortest next operation among jobs with operations left, breaking ties by job number, and decodes that list in the same way. This is a priority-list baseline; it is not a clock-driven shop-floor dispatcher. Its schedule and makespan are saved in `baselines.json` outside the search budget.

## Test cases

All algorithms use the same JSON files. A pair `[machine, duration]` describes an operation; pairs in a job must remain in order.

| Case | What it checks | Proven optimum |
| --- | --- | --- |
| single | One job, repeated use of one machine | 5 |
| bottleneck | Three jobs competing for one machine | 9 |
| crossed | Two jobs can run together on different machines | 5 |
| unequal | Different operation counts and a repeated machine | 5 |
| idle_gap | A later priority can fit in an earlier machine gap | Not supplied |
| synthetic_6x6 | Balanced jobs and machines | Not supplied |
| synthetic_10x5 | More jobs than machines | Not supplied |
| synthetic_5x10 | More machines than jobs | Not supplied |
| synthetic_15x10 | Larger operation set | Not supplied |

The small optimum values have hand-checkable explanations in the input files and are checked by enumerating all distinct priority lists in the tests. The larger cases use fixed random seeds recorded in their sources. They test software behavior and instance shape. They are not substitutes for the proposal's planned public benchmark study.

To use public instances, obtain the `jobshop1` text file from the [OR-Library source named in the proposal](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/jobshopinfo.html), then run:

```sh
python3 -m jssp --instances /path/to/jobshop1.txt --orlib-name ft06 --budget 10000 --repeats 20
```

This reader accepts a named instance in the original format. It does not guess a best-known solution. To report RPD, convert a verified instance to the JSON format and provide `bks` plus the value's reference in `source`. A **best-known solution (BKS)** is only a proven optimum if its source proves it. RPD is `100 * (makespan - bks) / bks`; missing BKS produces an empty RPD field.

## Telemetry and comparison

| File | Contents |
| --- | --- |
| telemetry.jsonl | Flushed after each candidate: run ID, seed, algorithm, evaluation, current and best makespan, elapsed seconds |
| runs.csv | One row per successful run, including instance size, job/machine ratio, runtime and RPD |
| summary.csv | Per instance and algorithm: count, best, mean, median, sample standard deviation, mean runtime and mean RPD |
| metadata.json | Full input snapshots, input SHA-256 hashes, arguments, parameter overrides, Python, machine information and Git revision |
| baselines.json | SPT schedules and makespans |
| failures.jsonl | Input/run errors with context and traceback; an empty file means no recorded failures |
| 0-ga-0.json, etc. | Effective parameters, best priority list, validated schedule and full convergence history |
| report.html | Offline convergence plots, Gantt charts and exact schedule tables |

`input_index` and run IDs distinguish files even if their names match. A failed run is not included in successful-run statistics; inspect failure counts alongside those statistics. Any recorded failure makes the command return exit code 1. Input validation and configuration errors may stop the command before runs begin. Telemetry is flushed continuously; completed run JSON and CSV files are saved after each run. An interrupted process can leave a report marked running and an incomplete summary.

Compare algorithms at equal evaluation budgets rather than equal iteration counts: one population step evaluates many candidates, while one SA step evaluates one. Runtime includes progress callbacks, file writes and live report rendering, so use the same reporting setup across methods and treat these as observed script runtimes. Initialization costs differ. The same seed numbers do not make the four random searches identical.

Parameters can be set in a JSON file, for example `{"ga":{"population":30,"mutation":0.3},"sa":{"temperature":30,"cooling":0.999}}`, passed with `--parameters path/to/parameters.json`. Default values are teaching starting points, not tuned research settings. Effective values are saved in every run JSON; fields for other algorithms are inactive. The public experiment below uses 18 verified benchmark instances and 20 seeds per instance, with the existing defaults frozen in advance. No parameter tuning was performed. A later study can tune on separate pilot instances and rerun the same protocol. Summary statistics are descriptive; no Friedman or post-hoc test is implemented.


## Public benchmark experiment

The experiment follows the proposal's sections III–IV: classical JSSP, a shared decoder and validator, an SPT baseline, equal candidate-evaluation budgets, 18 public instances and 20 seeds. The GA and ACO mechanisms still follow the supplied lecture materials as explained in their approach READMEs.

### Data and BKS verification

The selection was fixed before looking at the results: all three Fisher–Thompson cases, then the first two Lawrence cases from each size group, using only LA36 from the final 15×15 group to reach 18. This covers nine sizes, from 6×6 through 30×10, and job-to-machine ratios from 1 to 4. It is a selected sample from two benchmark families, not a random sample of all JSSP problems.

Data comes from [OR-Library jobshop1](https://people.brunel.ac.uk/~mastjjb/jeb/orlib/files/jobshop1.txt), named in the proposal. Every machine/duration pair was compared with [JSPLIB at revision eea2b60](https://github.com/tamy0612/JSPLIB/tree/eea2b60dd7e2f5c907ff7302662c61812eb7efdf). Every BKS was checked against its [optimum catalogue](https://github.com/tamy0612/JSPLIB/blob/eea2b60dd7e2f5c907ff7302662c61812eb7efdf/instances.json) and [ScheduleOpt's bounds at revision 824cf4d](https://github.com/ScheduleOpt/benchmarks/blob/824cf4d53117c6d64bb952c337ff73eacb363a5f/jobshop/solutions/bks.json). In all 18 cases the values agree, and ScheduleOpt reports a closed instance with equal lower and upper bounds. These are optima according to both catalogues; this project checks their agreement without reproducing mathematical proofs.

The [verification manifest](benchmarks/manifest.json) records the values, source records, URLs and SHA-256 hashes. Original downloaded files are retained in [benchmarks/sources](benchmarks/sources). The [importer](jssp/benchmarks.py) rejects disagreements in operation data, dimensions or BKS and rebuilds the experiment inputs offline:

```sh
python3 -m jssp.benchmarks
python3 -m unittest discover -s tests -v
```

### Frozen settings and reproduction

The [protocol](experiments/public-18/protocol.json) fixes all 18 inputs, all four algorithms, seeds 0–19, 1,000 candidate evaluations per run and the original parameter defaults. Initialization, rejected candidates and duplicate candidates all count. There are no early exits on reaching BKS. Small timing checks used seed 99 solely to estimate execution cost; no parameters were selected from their solution quality.

```sh
python3 -m jssp --instances instances/public/*.json --algorithms ga dpso aco sa --budget 1000 --repeats 20 --seed 0 --quiet --output results/public-18-1000
python3 scripts/audit_public_results.py results/public-18-1000
```

Use a new output directory when rerunning. The recorded run used Python 3.14.3; exact Python and machine details and the measured source revision are in [metadata.json](experiments/public-18/metadata.json). Runs execute sequentially on the same machine. Observed runtimes include telemetry and report work and should not be read as isolated algorithm timings. The browser report is refreshed at most once every two seconds across the experiment.

### Results from 21 November 2026

All **1,440 runs** completed with **zero failures**, using **1,440,000 candidate evaluations**. The audit reproduced every reported best schedule from its priority list, checked precedence and machine capacity, matched every telemetry event to its saved run history, and independently recomputed the summary statistics. The measured solver and runner revision is `af3cb92`.

The following averages give each of the 18 instances equal weight because each has the same 20 seeds. **RPD** measures the percentage above the verified optimum; lower is better. An optimum hit means one run finished at that instance's BKS. Tied lowest mean makespans count for every tied algorithm, so the last column can total more than 18.

| Algorithm | Mean RPD | Mean observed seconds/run | Runs reaching BKS (of 360) | Lowest mean makespan (ties included, of 18) |
| --- | ---: | ---: | ---: | ---: |
| GA | 8.60% | 0.128 | 65 | 2 |
| DPSO | 9.18% | 0.176 | 71 | 2 |
| ACO | 16.61% | 1.118 | 0 | 0 |
| SA | 6.88% | 0.119 | 97 | 17 |

SA has the smallest average deviation in this experiment. It has the lowest mean makespan on 17 instances when ties are included; DPSO has the lower mean on the remaining instance, FT06. GA and DPSO also tie SA on some easier cases. ACO has the largest average deviation with the current settings. These results compare these four implementations, defaults and budget; they do not establish that one algorithm is best for all scheduling problems.

Each cell below is **mean makespan (sample standard deviation)** across 20 seeds. Bold cells have the lowest mean in their row, including ties. The CSV files retain full precision, medians, best values, RPD and runtime.

| Instance | Jobs × machines | Verified BKS | GA | DPSO | ACO | SA |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| ft06 | 6 × 6 | 55 | 56.55 (1.85) | **55.45 (1.15)** | 59.20 (0.70) | 55.45 (1.15) |
| ft10 | 10 × 10 | 930 | 1067.00 (30.41) | 1072.35 (19.33) | 1107.45 (14.29) | **1053.40 (32.97)** |
| ft20 | 20 × 5 | 1165 | 1357.70 (28.47) | 1379.50 (20.34) | 1351.20 (16.43) | **1317.90 (33.38)** |
| la01 | 10 × 5 | 666 | 688.50 (13.13) | 686.00 (12.37) | 749.55 (14.26) | **674.20 (11.87)** |
| la02 | 10 × 5 | 655 | 712.45 (23.52) | 729.00 (14.81) | 739.00 (14.86) | **700.30 (20.00)** |
| la06 | 15 × 5 | 926 | **926.00 (0.00)** | **926.00 (0.00)** | 980.65 (11.51) | **926.00 (0.00)** |
| la07 | 15 × 5 | 890 | 907.55 (15.31) | 912.30 (11.05) | 962.65 (22.76) | **894.20 (8.46)** |
| la11 | 20 × 5 | 1222 | **1222.00 (0.00)** | 1222.10 (0.45) | 1296.40 (16.00) | **1222.00 (0.00)** |
| la12 | 20 × 5 | 1039 | 1040.80 (3.32) | 1041.75 (4.08) | 1132.20 (14.12) | **1040.05 (2.96)** |
| la16 | 10 × 10 | 945 | 1006.90 (15.70) | 1011.95 (15.75) | 1064.30 (15.41) | **993.15 (16.88)** |
| la17 | 10 × 10 | 784 | 831.20 (20.01) | 837.10 (12.76) | 901.05 (16.26) | **819.85 (19.70)** |
| la21 | 15 × 10 | 1046 | 1225.95 (25.65) | 1233.90 (10.67) | 1309.90 (25.07) | **1205.75 (17.34)** |
| la22 | 15 × 10 | 927 | 1092.65 (25.14) | 1103.80 (27.11) | 1214.75 (16.61) | **1066.40 (32.53)** |
| la26 | 20 × 10 | 1218 | 1400.15 (29.13) | 1413.50 (15.58) | 1573.40 (26.37) | **1357.00 (20.68)** |
| la27 | 20 × 10 | 1235 | 1453.20 (16.04) | 1468.20 (13.47) | 1588.35 (17.83) | **1419.20 (23.24)** |
| la31 | 30 × 10 | 1784 | 1884.15 (23.42) | 1890.30 (15.37) | 2078.95 (21.48) | **1848.25 (30.46)** |
| la32 | 30 × 10 | 1850 | 1977.40 (28.61) | 1991.00 (11.17) | 2187.00 (18.52) | **1954.35 (30.80)** |
| la36 | 15 × 15 | 1268 | 1440.50 (28.66) | 1448.15 (14.80) | 1590.15 (22.35) | **1422.80 (22.94)** |

To examine the proposal's question about instance size, this table groups the mean RPD by jobs and machines. Each instance has equal weight within its size group. Some groups contain only one instance, so these are descriptions of this sample, not reliable estimates for every problem of that size.

| Jobs × machines | Instances | GA mean RPD | DPSO mean RPD | ACO mean RPD | SA mean RPD |
| --- | ---: | ---: | ---: | ---: | ---: |
| 6 × 6 | 1 | 2.82% | 0.82% | 7.64% | 1.00% |
| 10 × 5 | 2 | 6.07% | 7.15% | 12.68% | 4.07% |
| 15 × 5 | 2 | 0.99% | 1.25% | 7.03% | 0.24% |
| 10 × 10 | 3 | 9.10% | 9.72% | 15.54% | 7.65% |
| 20 × 5 | 3 | 5.57% | 6.23% | 10.35% | 4.41% |
| 15 × 10 | 2 | 17.54% | 18.52% | 28.14% | 15.16% |
| 20 × 10 | 2 | 16.31% | 17.47% | 28.90% | 13.16% |
| 15 × 15 | 1 | 13.60% | 14.21% | 25.41% | 12.21% |
| 30 × 10 | 2 | 6.25% | 6.79% | 17.37% | 4.62% |

### Saved evidence and limits

- [Per-seed results](experiments/public-18/runs.csv): all 1,440 outcomes and evaluation counts.
- [Per-instance summaries](experiments/public-18/summary.csv): best, mean, median, sample standard deviation, RPD and observed runtime.
- [Convergence across all seeds](experiments/public-18/convergence.csv): mean best makespan and RPD at evaluation 1 and every 100 evaluations.
- [SPT baseline schedules](experiments/public-18/baselines.json).
- [All validated final schedules](experiments/public-18/solutions.jsonl.gz): gzip-compressed JSON Lines containing every seed's best priority list and schedule.
- [Best-run histories](experiments/public-18/best-runs.json.gz): 72 full run records, one best run for each instance and algorithm.
- [Audit record](experiments/public-18/audit.json): coverage, validation checks, measured source revision and SHA-256 hashes of every full local run file and telemetry/report file.

The complete local output, including all candidate telemetry, all per-run histories and the HTML report, is in `results/public-18-1000` (about 442 MB for this execution). It is ignored by Git; the compact evidence above is committed. Regenerate the complete output with the reproduction command, or render the archived best-run histories without rerunning the algorithms:

```sh
python3 - <<'PYTHON'
import gzip
import json
from pathlib import Path
from jssp.report import write_report

Path('results').mkdir(exist_ok=True)
runs = json.loads(gzip.decompress(Path('experiments/public-18/best-runs.json.gz').read_bytes()))
write_report('results/public-18-best.html', runs)
PYTHON
```

The budget is 1,000 evaluations per run and the parameters were not tuned. The sample covers two classic families and several size groups contain only one or two instances. Runtime includes disk writes and report updates, and different seeds may incur different report work. No statistical significance test or new proof of optimality was performed. A larger budget, balanced tuning on separate pilot cases, more benchmark families and paired statistical tests would be needed before making broader recommendations.
