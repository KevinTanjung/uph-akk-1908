# Genetic Algorithm (GA)

GA improves a population of job priority lists through selection, crossover and mutation. Every list is scored by the [shared decoder](../../README.md#scheduling-model).

## Chromosome and selection

For job $j$ with $n_j$ operations, chromosome $x$ contains exactly $n_j$ copies of $j$. Its makespan is $C(x)$. Shorter schedules receive greater fitness and selection probability:

$$
f(x)=\frac{1}{C(x)},\qquad
P(x_i)=\frac{f(x_i)}{\sum_{r=1}^{P}f(x_r)}.
$$

Here $P$ is population size. Two parents are drawn independently with these probabilities.

## Crossover and mutation

With probability $p_c$, select a subset of jobs $S$, including each job independently with probability $1/2$. Keep their positions from parent $a$ and fill the gaps in parent $b$'s order, skipping jobs in $S$:

$$
c_i=\begin{cases}
a_i,&a_i\in S,\\
\text{next entry of }b\text{ whose job is outside }S,&a_i\notin S.
\end{cases}
$$

For $a=[0,1,2,0,1,2]$, $b=[2,1,0,1,2,0]$ and $S=\{1\}$, the child is $c=[2,1,0,2,1,0]$. Each job still occurs twice. Without crossover, copy parent $a$.

With probability $p_m$, swap two distinct positions:

$$
c'=\operatorname{swap}(c,u,v),\qquad u\ne v.
$$

Both operators preserve job counts. Swapping identical values leaves the list unchanged but still spends an evaluation.

## Replacement and budget

Keep one evaluated elite, then fill the remaining population with evaluated children. Stop after exactly $B$ candidate evaluations, allowing a partial final generation. Return the best list seen; retaining the elite does not spend another evaluation.

| Setting | Default | Pilot-selected |
| --- | ---: | ---: |
| Population $P$ | 20 | 20 |
| Crossover $p_c$ | 0.8 | 0.8 |
| Mutation $p_m$ | 0.2 | 0.2 |

The defaults won the pilot search. A population can lose variety, so repeated seeds and convergence traces matter. See the [experiment overview](../../README.md#results).
