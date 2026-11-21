# Genetic Algorithm (GA)

The supplied `12 00 Genetic Algorithm.pptx` introduces a population of chromosomes on slide 2, the search loop on slide 4, roulette-wheel selection on slide 7, crossover on slides 9–10 and mutation on slide 12. The proposal, section III.A, requires an encoding that works for job-shop scheduling.

A **chromosome** here is a priority list of job numbers. Each **gene** is one occurrence of a job and selects its next operation. The number of occurrences stays equal to that job's operation count. This replaces the lecture's binary encoding for a numerical problem.

The initial **population** contains shuffled copies of the required job occurrences. The decoder computes each chromosome's makespan. **Fitness** is `1 / makespan`, so a shorter schedule gets a larger roulette-wheel selection weight.

**Selection** draws two parents using those weights. **Crossover**, used with probability 0.8, chooses a random subset of jobs. It keeps all occurrences of those jobs at their positions in the first parent and fills other positions in the second parent's order. This preserves every job's occurrence count. Direct one-point crossover from the binary example could lose or duplicate operations, so it is not used here.

**Mutation**, with probability 0.2 per child, swaps two positions. The decoder still schedules the first occurrence of a job before its second occurrence. Swapping identical job numbers leaves the candidate unchanged and still spends an evaluation.

**Elitism** keeps the best chromosome from the previous generation. Other positions are filled with evaluated children. The default population is 20. The search stops exactly at the candidate budget, including a partial last generation. The returned result is the best candidate seen throughout the run.

See [the shared README](../../README.md) for execution, decoder rules and telemetry. This is a simple scheduling adaptation of the lecture mechanism, not a reproduction of Cheng et al.'s survey or a claim of optimality. A population can lose variety and settle early; inspect convergence across several seeds.
