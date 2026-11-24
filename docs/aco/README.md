# Ant Colony Optimization (ACO)

ACO builds priority lists one operation at a time, then reinforces transitions used by shorter schedules. Completed lists use the [shared decoder](../../README.md#scheduling-model).

## Construct a candidate

Operation $o=(j,k)$ identifies operation $k$ of job $j$. The eligible set $E$ contains the next unscheduled operation of each unfinished job. From previous operation $a$ (or a start node), choose $o\in E$ with probability

$$
\eta_o=\frac{1}{d_o},\qquad
P(o\mid a,E)=\frac{\tau_{ao}^{\alpha}\eta_o^{\beta}}
{\sum_{v\in E}\tau_{av}^{\alpha}\eta_v^{\beta}}.
$$

Here $d_o$ is processing duration, $\tau_{ao}$ is transition pheromone, $\alpha$ controls pheromone weight, and $\beta$ controls preference for shorter operations. Initially $\tau_{ao}=1$.

For equal pheromone and durations 2 and 4, $\beta=2$ gives probabilities $0.8$ and $0.2$; $\beta=1$ gives $2/3$ and $1/3$. Append the chosen job to the list, update eligibility, and repeat until all $N$ operations are included. There is no return-to-start edge.

## Update pheromone

After a colony is evaluated, evaporate first and then add deposits from every ant:

$$
\tau_{ao}'=\max\left(10^{-12},(1-\rho)\tau_{ao}\right)
+\sum_{r=1}^{m}\frac{Q}{C(x_r)}
\mathbf{1}\!\left[(a,o)\in\operatorname{path}(x_r)\right].
$$

Here $\rho$ is evaporation, $Q$ is deposit strength, $m$ is the completed colony size, and the indicator is 1 when ant $r$ used that transition. Smaller makespans deposit more pheromone. The floor applies before deposits.

## Budget and settings

Each completed ant spends one evaluation. A partial final colony respects the exact budget $B$. Keep the best list across all colonies. The transition table has $N(N+1)$ entries, so equal evaluation counts do not imply equal runtime across algorithms.

| Setting | Default | Pilot-selected |
| --- | ---: | ---: |
| Colony size | 20 | 20 |
| Pheromone weight $\alpha$ | 1 | 1 |
| Duration weight $\beta$ | 2 | 1 |
| Evaporation $\rho$ | 0.1 | 0.2 |
| Deposit $Q$ | 1 | 10 |

The short-operation heuristic cannot anticipate every machine conflict. See the [experiment overview](../../README.md#results) for outcomes across seeds and instances.
