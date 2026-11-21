# Materials and scope

The user supplied the following materials. Their SHA-256 hashes are recorded in `materials.json` so the exact source versions can be identified. The original teaching files are not redistributed here.

| Material | Where it informs this implementation |
| --- | --- |
| Proposal_UTS_KK_JSSP_Komparasi_4_Metaheuristik.pdf | III.A: classical JSSP model, makespan, four mechanisms and valid decoder. III.B: SPT baseline and evaluation counts. IV.A–C: instance checks, seeds, runtime, RPD, stability and schedule validation. |
| 12 00 Genetic Algorithm.pptx, Samuel Lukas | Slides 2 and 4: chromosomes, population and search loop. Slide 7: roulette-wheel selection. Slides 9–10: crossover. Slide 12: mutation. Scheduling operators replace the binary numerical example. |
| 12 00 Ant Colony Optimation.pptx, Samuel Lukas | Slides 3 and 5: pheromone update and normalized choice weights. Slides 6–7: route examples. Slide 9: construction followed by pheromone update. Operation transitions replace route edges. |
| Simulasi ACO 01.xlsx | First worksheet: two-route probability, evaporation and deposits. H3=0.1, I3=1, J3=1; D4=(1-H3)*D3+O3; E4=(1-H3)*E3+P3. Formula XML and stored values were inspected without changing the workbook. |

The source proposal cites Cheng, Gen and Tsujimura (1996) for GA representation; Blum and Sampels (2004) for ACO; Sha and Hsu (2006) for discrete PSO; and van Laarhoven, Aarts and Lenstra (1992) for SA. Their full texts have not been verified in this implementation task. These are references from the supplied proposal, not claims that the programs reproduce those papers.

The proposal plans 18 verified public instances and 20 independent runs per combination. The bundled nine cases establish software checks and demonstrate different instance shapes. Four have exhaustively checked optima; five have no BKS supplied. No public benchmark values, significance claims or research results are invented. The public study now adds 18 OR-Library instances, with operation data checked against pinned JSPLIB data and BKS checked against JSPLIB and ScheduleOpt catalogues. The source snapshots, hashes and records are in `benchmarks/manifest.json`; settings and results are in `experiments/public-18`. The mathematical optimality proofs were not reproduced. Synthetic case generation uses Python's seeded random shuffle and durations from 1 through 30, as recorded in each file.

The shared decoder inserts each operation into the earliest fitting machine gap after its predecessor. GA uses job-subset crossover instead of binary one-point crossover. DPSO uses swap lists and no tabu search. ACO uses operation transitions, inverse duration and sampled ants. SA uses swap neighbors and geometric cooling. These are explicit project choices consistent with the proposal's broad mechanisms, not details established by the lecture examples.
