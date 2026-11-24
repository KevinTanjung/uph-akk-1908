# Simulated Annealing (SA)

SA follows one current job priority list while retaining the best list seen. A neighbor swaps two distinct positions, preserving job counts. Both lists use the [shared decoder](../../README.md#scheduling-model).

## Neighbor and acceptance

Start from a shuffled list $x$. Propose $y=\operatorname{swap}(x,u,v)$ and calculate

$$
\Delta=C(y)-C(x),\qquad
P(\text{accept }y)=\begin{cases}
1,&\Delta\le 0,\\
\exp(-\Delta/T),&\Delta>0.
\end{cases}
$$

An improvement or tie is always accepted. For a worse move, draw $r\sim U[0,1)$ and accept when $r<\exp(-\Delta/T)$. For $\Delta=10$, acceptance is about $0.6065$ at $T=20$ and $0.0000454$ at $T=1$.

The best evaluated list $x^*$ is retained separately:

$$
x^*\leftarrow y\quad\text{if }C(y)<C(x^*).
$$

Accepting a worse current list therefore does not erase a better saved answer.

## Cooling and budget

After every proposal, including a rejected one, cool geometrically:

$$
T_{t+1}=\max(10^{-12},\gamma T_t),\qquad 0<\gamma<1.
$$

One initial evaluation plus $B-1$ proposals uses budget $B$. Return $x^*$, which may differ from the final current list.

| Setting | Default | Pilot-selected |
| --- | ---: | ---: |
| Initial temperature $T_0$ | 20 | 20 |
| Cooling rate $\gamma$ | 0.995 | 0.9995 |

After 1,000 cooling steps, the temperatures are approximately $0.1331$ and $12.1291$. Slower cooling allows uphill moves for longer; its usefulness must be measured. Temperature uses the same scale as makespan differences. See the [experiment overview](../../README.md#results).
