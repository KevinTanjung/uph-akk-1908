# Discrete Particle Swarm Optimization (DPSO)

The proposal, section III.A and reference [8], calls for a discrete position and movement design. A real-valued PSO update cannot directly operate on a list of job numbers. The supplied slides do not provide a full DPSO implementation; the design below is this project's explicit adaptation, not a reproduction of Sha and Hsu's hybrid method.

A particle's **position** is a job priority list. Its **velocity** is an ordered list of index swaps. Swaps preserve the number of operations for every job. Each particle remembers its own best position (**personal best**), while the swarm remembers the best position found by any particle (**global best**).

To move toward a target list, scan from left to right. At each mismatch, find the needed job later in a working copy and record the swap that puts it in place. Applying every recorded swap would reach that target, including when jobs occur several times.

The next velocity combines three lists: retained old swaps (**inertia**), swaps toward personal best (**cognitive** movement), and swaps toward a snapshot of global best (**social** movement). Each swap is independently kept with probability 0.5 for its part. Lists are concatenated in that order and capped at twice the number of operations to prevent unbounded velocity growth. Because these are sampled and combined movements, a step need not improve the schedule or reach either target.

Apply the swaps in order. With probability 0.2, add a random two-position mutation so an identical swarm can still explore. Evaluate the new position with the shared decoder, then update personal and global best when makespan improves. The default swarm has 20 particles. Initialization counts toward the budget; the final swarm step may be partial.

See [the shared README](../../README.md) for execution and result files. This implementation does not include the paper's Giffler–Thompson decoder or tabu search. Its behavior must be assessed on the actual selected instances and settings.
