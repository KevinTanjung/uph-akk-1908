# Simulated Annealing (SA)

The proposal, section III.A and reference [9], defines SA as a search that changes one solution and sometimes accepts a worse one. That is the meaning of SA in this repository. The final two ACO lecture slides use “SA” while describing swarms and particles; they do not define Simulated Annealing and are not used as its instructions.

The initial solution is a shuffled job priority list. A **neighbor** swaps two randomly selected positions. This keeps the operation counts unchanged. The shared decoder computes its makespan.

Let **delta** be the neighbor's makespan minus the current makespan. If delta is zero or negative, accept the neighbor. Otherwise accept it with probability `exp(-delta / temperature)`. This gives the search a chance to leave a local minimum. The best solution seen is stored separately, so accepting a worse current solution does not lose an earlier result.

**Temperature** starts at 20 time units. After each proposed neighbor it is multiplied by the **cooling rate**, 0.995, down to a numerical floor of `1e-12`. High temperatures make worse steps more likely. As temperature falls, the search becomes less willing to accept them. These defaults are starting settings; a problem with much larger processing times may need a different temperature.

One initial candidate and every proposed neighbor count toward the same budget used by GA, DPSO and ACO. Rejected neighbors still count. Unlike those three methods, SA maintains one current solution rather than a population. It returns the best solution seen, not necessarily the last accepted solution.

See [the shared README](../../README.md) for commands and telemetry. This simple swap neighborhood and geometric cooling schedule implement the proposal's mechanism; they do not reproduce every detail of van Laarhoven et al.'s method or prove global optimality.
