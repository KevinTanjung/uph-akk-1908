# A Comparative Study of Four Metaheuristics for Job-Shop Scheduling Under Equal Evaluation Budgets

**Abstract—** This study compares Genetic Algorithm (GA), Discrete Particle Swarm Optimization (DPSO), Ant Colony Optimization (ACO), and Simulated Annealing (SA) for classical job-shop scheduling. All methods share an operation representation, schedule decoder, validator, and makespan objective. Experiments use 18 public benchmark instances and 20 seeds per method, with 1,000- and 10,000-evaluation budgets. A subsequent equal-budget search selects parameters on four separate pilot instances before repeating the 10,000-evaluation experiment. The pilot-selected mean relative percentage deviations are 5.4768% for GA, 5.6277% for DPSO, 15.3070% for ACO, and 3.3629% for SA. Friedman and Holm-corrected Wilcoxon tests indicate differences among methods, while selected GA and DPSO are not statistically separated. DPSO shows a significant improvement after tuning. The findings concern the tested implementations and benchmark sample.

**Index Terms—** Job-shop scheduling, metaheuristics, makespan, parameter tuning, statistical comparison.

## I. Introduction

Job-shop scheduling assigns ordered job operations to shared machines. The objective is to complete all work as early as possible while respecting machine capacity and job precedence. This study examines how four search mechanisms perform when schedule construction and candidate-evaluation budgets are held constant.

The contribution is a reproducible comparison: a common scheduling pipeline, repeated seeded experiments, separate pilot-based parameter selection, live convergence and schedule visualization, and auditable statistical evidence. The study evaluates these implementations; it does not introduce a new optimization algorithm.

<a id="scheduling-model"></a>

## II. Problem Formulation

Job $j$ consists of operations $O_{j,k}$ with fixed machine $m_{j,k}$, duration $d_{j,k}$, start $S_{j,k}$, and completion $C_{j,k}$. The objective and precedence constraints are

$$
\min C_{\max}=\max_{j,k}C_{j,k},\qquad
C_{j,k}=S_{j,k}+d_{j,k},\qquad
S_{j,k+1}\ge C_{j,k},\qquad S_{j,k}\ge0.
$$

For any operations $a,b$ assigned to the same machine,

$$
C_a\le S_b\quad\lor\quad C_b\le S_a.
$$

Operations are nonpreemptive, all jobs are available at time zero, and machines process one operation at a time. Setup times, deadlines, breakdowns, and alternative machine assignments are excluded.

## III. Methodology

### A. Common Representation and Evaluation

A candidate $x$ is a priority list in which job $j$ occurs once per operation. Successive occurrences select successive operations of that job. A decoder inserts each operation into the earliest available machine gap after its predecessor finishes. The resulting objective is $C(x)=C_{\max}$. A validator checks operation coverage, machine assignments, durations, precedence, and overlap.

Each algorithm receives exactly $B$ decoded candidate evaluations. Initialization, repeated candidates, and rejected SA proposals count; retaining an evaluated GA elite does not. The returned solution is the best evaluated candidate. A separate Shortest Processing Time (SPT) priority-list baseline is recorded outside the search budget.

### B. Search Mechanisms

| Method | Formulation and search mechanism | Detailed definition |
| --- | --- | --- |
| GA | Fitness $f(x)=1/C(x)$ drives roulette selection; job-subset crossover and swap mutation preserve operation counts; elitism retains one candidate. | [Chromosome and operators](docs/ga/README.md) |
| DPSO | Ordered swap lists combine sampled inertia, personal-best, and global-best movements; an additional swap mutation supports exploration. | [Discrete movement equations](docs/dpso/README.md) |
| ACO | Eligible operations are sampled with weights $\tau^\alpha(1/d)^\beta$; evaporation and deposits $Q/C(x)$ update transition pheromone. | [Construction and pheromone equations](docs/aco/README.md) |
| SA | Swap neighbors with $\Delta=C(y)-C(x)>0$ are accepted with probability $e^{-\Delta/T}$; geometric cooling reduces $T$. | [Acceptance and cooling equations](docs/sa/README.md) |

## IV. Experimental Design

The evaluation includes 18 instances from the Fisher–Thompson and Lawrence families, spanning nine job–machine sizes. Operation data and reference values were cross-checked; the [verification manifest](benchmarks/manifest.json) records provenance and hashes. Each campaign evaluates four algorithms with seeds 0–19, totaling 1,440 runs. Fixed defaults are compared at $B=1{,}000$ and $B=10{,}000$.

Pilot tuning evaluates four configurations per algorithm on LA03, LA13, LA23, and LA37 using seeds 100–102 and $B=10{,}000$. The configuration with the lowest pilot mean relative percentage deviation (RPD) is selected; ties favor the lower configuration index. One setting per method is then frozen for the final benchmark campaign. Pilot and final instances and seeds are disjoint. GA retains its defaults. Tuning adds 1.92 million evaluations; each 10,000-evaluation benchmark campaign uses 14.4 million.

Quality is expressed relative to each instance's best-known solution (BKS):

$$
\mathrm{RPD}=100\frac{C_{\max}-\mathrm{BKS}}{\mathrm{BKS}}.
$$

Reported aggregate RPD gives each instance equal weight after averaging its 20 seeds. Statistical analysis uses 18 paired instance means, rather than treating all seeded runs as independent problems. A tie-corrected Friedman test includes a 99,999-draw within-instance permutation check. Exact two-sided Wilcoxon signed-rank tests use Holm correction across six algorithm pairs. A separate four-test family assesses tuning changes. The significance threshold is 0.05.

<a id="results"></a>

## V. Results and Discussion

**TABLE I. MEAN RPD ACROSS 18 INSTANCES (LOWER IS BETTER)**

| Algorithm | Default, $B=1{,}000$ | Default, $B=10{,}000$ | Pilot-selected, $B=10{,}000$ |
| --- | ---: | ---: | ---: |
| GA | 8.60% | 5.4768% | 5.4768% |
| DPSO | 9.18% | 6.7817% | 5.6277% |
| ACO | 16.61% | 15.6841% | 15.3070% |
| SA | 6.88% | 3.6189% | 3.3629% |

Larger default budgets reduce aggregate RPD for every method. Following pilot selection, SA has the lowest aggregate RPD, followed by GA, DPSO, and ACO. All final schedules and histories pass the recorded audits.

The selected-setting Friedman statistic is 44.281437 with three degrees of freedom. Its permutation $p=0.000010$ is the sampling resolution, not a zero probability; Kendall's $W=0.8200$. Five of the six Holm-corrected algorithm-pair comparisons are significant: SA has lower RPD than the other methods and ACO has higher RPD. GA versus DPSO is not significantly separated ($p=0.80395508$), although their aggregate means differ. Both default campaigns separate all six pairs at the corrected threshold.

DPSO improves 14 instance means, ties four, and worsens none after tuning. Its aggregate reduction is 1.1540 RPD percentage points, with corrected $p=0.00048828$. ACO and SA reduce their aggregate means by 0.3771 and 0.2560 points, respectively, but their corrected tuning-change tests are not significant ($p=0.45750427$ and $p=0.06298828$). GA's outcomes are unchanged because the defaults won its pilot search. Statistical significance and the size of an improvement answer different questions; a nonsignificant result does not establish equality.

## VI. Limitations

The sample contains two benchmark families and the pilot search examines only four configurations per algorithm. Earlier benchmark outcomes were already known before the pilot follow-up, although selection used only pilot scores; the extension is exploratory. Signed-rank inference assumes symmetric paired differences under the null. The named Holm corrections do not cover every analysis conducted during development. Equal evaluation budgets do not imply equal runtime, and measured runtime includes reporting and file writes. These results neither establish a universal algorithm ranking nor prove optimality of heuristic schedules.

## VII. Conclusion

A shared representation and evaluation pipeline enables a controlled comparison of four scheduling searches. Increasing the evaluation budget improves recorded solution quality, and separate pilot selection substantially improves DPSO in this study. SA achieves the lowest aggregate RPD, while selected GA and DPSO cannot be reliably ordered by the paired test. Reporting instance-level effects alongside corrected tests prevents a small average advantage from being interpreted as a general performance claim.

## Reproducibility and Implementation

Python 3.9+ runs the scheduler without extra packages. From the repository root:

```sh
python3 -m jssp --instances instances/crossed.json --budget 1000 --repeats 2 --output results/demo
python3 -m unittest discover -s tests -v
```

Terminal progress and the generated `report.html` show convergence and machine Gantt charts during execution. Each campaign records candidate telemetry, full histories, validated schedules, CSV summaries, settings, input hashes, and failure records. Raw output remains local under ignored `results/`; compact evidence is versioned. Use a fresh output directory for each campaign.

| Study record | Evidence |
| --- | --- |
| Default, 1,000 evaluations | [Outcomes and statistical analysis](experiments/public-18) |
| Default, 10,000 evaluations | [Outcomes and budget comparison](experiments/public-18-10000) |
| Pilot selection | [Candidate configurations, scores, and selection](experiments/pilot-tuning) |
| Selected, 10,000 evaluations | [Outcomes, audits, and statistical comparisons](experiments/public-18-tuned) |

See [experiment reproduction](docs/experiments.md) for full execution and analysis commands. Statistical analysis uses the pinned dependencies in `requirements-statistics.txt`. Exact reproduction requires the recorded inputs, settings, seeds, and software versions; observed runtimes vary.
