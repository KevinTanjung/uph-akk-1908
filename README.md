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

The script prints the report location and progress while it runs. Open `report.html` in a browser. It refreshes every two seconds during execution and shows candidate quality, best quality and the best schedule so far. The final report stops refreshing. Gantt bars show when each machine works on each job; hover over a bar for exact times, or expand the schedule table. Report time units match the input, rather than assuming minutes.

Use `--output results/my-experiment` to choose a new output folder. Existing folders are refused to protect earlier results. `--quiet` hides candidate progress while keeping telemetry and the report. Results stay local and are ignored by Git.

The default is all four algorithms, 1,000 candidate evaluations each and 20 runs with seeds 0–19. Change the algorithm list with `--algorithms ga dpso aco sa`, the budget with `--budget`, and the first seed with `--seed`. Reusing an input, algorithm, parameters and seed reproduces the schedule; runtime measurements vary. Every candidate evaluation counts, including initialization and repeated candidates. Keeping an already evaluated GA elite does not spend another evaluation. The final validation decodes the selected answer again without adding a search evaluation.

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

Parameters can be set in a JSON file, for example `{"ga":{"population":30,"mutation":0.3},"sa":{"temperature":30,"cooling":0.999}}`, passed with `--parameters path/to/parameters.json`. Default values are teaching starting points, not tuned research settings. Effective values are saved in every run JSON; fields for other algorithms are inactive. For the proposal's final study, select and verify the planned 18 benchmark instances and their BKS, tune on separate pilot instances, then freeze settings and run 20 seeds per instance. This repository does not claim those experiments or statistical significance have already been established. Summary statistics are descriptive; no Friedman or post-hoc test is implemented.
