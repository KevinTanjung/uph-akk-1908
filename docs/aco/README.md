# Ant Colony Optimization (ACO)

The supplied `12 00 Ant Colony Optimation.pptx` explains pheromone evaporation and deposits on slide 3, weighted route selection on slide 5, examples on slides 6–7, and the construction/update loop on slide 9. `Simulasi ACO 01.xlsx`, first worksheet, illustrates those updates for two routes. Its cells H3, I3 and J3 contain evaporation 0.1, alpha 1 and beta 1; D4 and E4 apply evaporation plus deposits. The lecture's slide 6 displays a different evaporation value; the workbook and slide examples should not be treated as one identical parameter setting.

An **ant** builds one job priority list. It can choose only the next unscheduled operation of each unfinished job. These are its eligible choices. Each selected operation is added once, so every completed candidate has the correct operation counts and job order.

**Pheromone** belongs to a directed transition between two operation identities, with an extra start node. It starts at 1. The **heuristic** for a choice is `1 / processing_duration`, which favors shorter operations. The probability of selecting an eligible operation is its `pheromone^alpha * heuristic^beta` weight divided by the sum of all eligible weights. Defaults are alpha 1 and beta 2. Beta 2 is a scheduling design choice, not a value copied from the workbook.

The decoder schedules each completed list and measures its makespan. After a colony of up to 20 ants, each pheromone value becomes `(1 - evaporation) * old_value`. Then each ant adds `deposit / makespan` to every transition it used. Defaults are evaporation 0.1 and deposit 1. A small positive floor of `1e-12` keeps long-unused transitions available. The next colony uses the updated pheromone.

This adapts the lecture's route length to schedule makespan and its route edges to operation transitions. The workbook uses fractional expected ant counts in its teaching example; this program samples individual ants instead. There is no return-to-start edge because a schedule is not a round trip. Optional local search in slide 9 is omitted. The best completed schedule is retained, and a partial last colony respects the evaluation budget.

See [the shared README](../../README.md) for execution and output. The shortest-operation heuristic does not anticipate every future machine conflict, and pheromone can concentrate too early. This is not a reproduction of Blum and Sampels' research implementation.
