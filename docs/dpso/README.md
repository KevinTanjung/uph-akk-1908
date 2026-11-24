# Discrete Particle Swarm Optimization (DPSO)

DPSO moves a swarm of job priority lists using ordered swaps. Particle $i$ has position $x_i$, previous velocity $V_i$, personal best $p_i$, and access to a snapshot $g$ of the best list at the start of each swarm sweep. All positions use the [shared decoder](../../README.md#scheduling-model).

## Discrete movement

Let $D(x,y)$ be the ordered swaps that transform $x$ into $y$. Scan left to right; at each mismatch, find the required job later in a working copy and swap it into place. For example:

$$
[0,1,0,1]\xrightarrow{(0,1)}[1,0,0,1]
\xrightarrow{(2,3)}[1,0,1,0].
$$

Positions are numbered from zero. Let $\mathcal{S}_q(V)$ retain each swap independently with probability $q$, $\oplus$ concatenate lists, and $\operatorname{take}_{2N}$ keep the first $2N$ swaps for $N$ operations:

$$
V_i'=\operatorname{take}_{2N}\left(
\mathcal{S}_{\omega}(V_i)
\oplus\mathcal{S}_{c_p}(D(x_i,p_i))
\oplus\mathcal{S}_{c_g}(D(x_i,g))\right).
$$

Apply these swaps in order, then perform one extra random swap with probability $p_m$:

$$
\tilde{x}_i=\operatorname{apply}(V_i',x_i),\qquad
x_i'=\begin{cases}
\operatorname{swap}(\tilde{x}_i,u,v),&\text{with probability }p_m,\\
\tilde{x}_i,&\text{otherwise}.
\end{cases}
$$

Both target differences are computed from the position before movement. Sampled swaps can cancel each other; movement need not improve makespan. The extra mutation is not stored in $V_i'$.

## Memory and budget

Evaluate $C(x_i')$ and replace $p_i$ only if $C(x_i')<C(p_i)$. Retain the best evaluated list globally. Initialization and every moved candidate count toward the exact budget $B$; the last sweep may be partial.

| Setting | Default | Pilot-selected |
| --- | ---: | ---: |
| Swarm size | 20 | 10 |
| Inertia $\omega$ | 0.5 | 0.3 |
| Personal-best probability $c_p$ | 0.5 | 0.7 |
| Global-best probability $c_g$ | 0.5 | 0.5 |
| Mutation $p_m$ | 0.2 | 0.4 |

This implementation uses swaps without additional local search. See the [experiment overview](../../README.md#results) for the measured effect of the selected settings.
