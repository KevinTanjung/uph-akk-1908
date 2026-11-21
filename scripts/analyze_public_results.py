"""Friedman and exact paired Wilcoxon/Holm analysis of the saved public experiment."""
import csv
import hashlib
import json
import math
import platform
import sys
from collections import defaultdict
from fractions import Fraction
from itertools import combinations
from pathlib import Path

import numpy as np
import scipy
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / 'experiments/public-18'
ALPHA = 0.05
PERMUTATIONS = 99_999
PERMUTATION_SEED = 20261121


def holm(pvalues):
    """Holm step-down adjustment across the complete pairwise test family."""
    adjusted = [0.0] * len(pvalues)
    previous = 0.0
    for position, index in enumerate(sorted(range(len(pvalues)), key=pvalues.__getitem__)):
        previous = min(1.0, max(previous, (len(pvalues) - position) * pvalues[index]))
        adjusted[index] = previous
    return adjusted


def load_blocks(folder=EXPERIMENT):
    folder = Path(folder)
    protocol = json.loads((folder / 'protocol.json').read_text())
    audit = json.loads((folder / 'audit.json').read_text())
    content = (folder / 'runs.csv').read_bytes()
    for name in ('runs.csv', 'metadata.json'):
        if hashlib.sha256((folder/name).read_bytes()).hexdigest() != audit['raw_sha256'][name]:
            raise ValueError(name + ' no longer matches the audited experiment')
    names, algorithms, seeds = protocol['instances'], protocol['algorithms'], protocol['seeds']
    expected = {(name, algorithm, seed) for name in names for algorithm in algorithms for seed in seeds}
    seen, groups = set(), defaultdict(list)
    for row in csv.DictReader(content.decode().splitlines()):
        key = row['instance'], row['algorithm'], int(row['seed'])
        makespan = int(row['makespan'])
        if key not in expected or key in seen or makespan <= 0 or int(row['evaluations']) != protocol['budget']:
            raise ValueError('unexpected, duplicated or invalid run')
        seen.add(key)
        groups[key[:2]].append(makespan)
    if seen != expected:
        raise ValueError('incomplete experiment')
    bks = {record['instance']['name']: record['instance']['bks']
           for record in json.loads((folder / 'metadata.json').read_text())['inputs']}
    if set(bks) != set(names) or any(type(value) is not int or value <= 0 for value in bks.values()):
        raise ValueError('missing or invalid BKS')
    # Integer totals preserve exact ties across 20-seed means; fractions avoid subtraction roundoff.
    totals = np.array([[sum(groups[name, alg]) for alg in algorithms] for name in names], dtype=np.int64)
    rpds = [[Fraction(100 * (int(value) - len(seeds) * bks[name]), len(seeds) * bks[name])
             for value in totals[i]] for i, name in enumerate(names)]
    return protocol, totals, rpds


def friedman(totals, permutations=PERMUTATIONS, seed=PERMUTATION_SEED):
    n, k = totals.shape
    ranks = stats.rankdata(totals, axis=1, method='average')
    tie_sum = sum(sum(count**3 - count for count in np.unique(row, return_counts=True)[1]) for row in totals)
    correction = 1 - tie_sum / (n * (k**3 - k))
    if correction == 0:
        raise ValueError('all algorithms tie on all instances')
    observed = stats.friedmanchisquare(*totals.T)

    def statistic(*columns, axis=-1):
        rank_sums = np.stack([np.sum(column, axis=axis) for column in columns], axis=-1)
        return (12 * np.sum(rank_sums**2, axis=-1) / (n * k * (k + 1)) - 3 * n * (k + 1)) / correction

    assert math.isclose(float(statistic(*ranks.T)), float(observed.statistic), abs_tol=1e-10)
    sampled = stats.permutation_test(tuple(ranks.T), statistic, permutation_type='samples',
                                     vectorized=True, n_resamples=permutations, batch=2048,
                                     alternative='greater', rng=np.random.default_rng(seed))
    tolerance = abs(float(sampled.statistic)) * np.finfo(float).eps * 100
    exceedances = int(np.count_nonzero(sampled.null_distribution >= sampled.statistic - tolerance))
    return dict(statistic=float(observed.statistic), degrees_of_freedom=k-1,
                chi_square_pvalue=float(observed.pvalue), permutation_pvalue=float(sampled.pvalue),
                permutation_draws=permutations, permutation_seed=seed, exceedances=exceedances,
                monte_carlo_resolution=1/(permutations+1), tie_correction=float(correction),
                kendalls_w=float(observed.statistic / (n*(k-1)))), ranks


def paired_test(differences):
    nonzero = np.array([float(d) for d in differences if d], dtype=float)
    if not len(nonzero):
        return dict(statistic=0.0, pvalue=1.0, nonzero_pairs=0, sign_assignments=1)
    signed_ranks = np.copysign(stats.rankdata(np.abs(nonzero), method='average'), nonzero)
    # Under sign flips the absolute ranks stay fixed: this is the exact Wilcoxon null.
    result = stats.permutation_test((signed_ranks,), lambda x, axis: np.sum(x, axis=axis),
                                    permutation_type='samples', vectorized=True, alternative='two-sided',
                                    n_resamples=np.inf, batch=4096)
    statistic = (np.sum(np.abs(signed_ranks)) - abs(float(result.statistic))) / 2
    return dict(statistic=float(statistic), pvalue=float(result.pvalue),
                nonzero_pairs=len(nonzero), sign_assignments=2**len(nonzero))


def main(folder=EXPERIMENT):
    folder = Path(folder)
    protocol, totals, rpds = load_blocks(folder)
    omnibus, ranks = friedman(totals)
    algorithms = protocol['algorithms']
    pairs = []
    for a, b in combinations(range(len(algorithms)), 2):
        differences = [row[a] - row[b] for row in rpds]
        pairs.append(dict(algorithm_a=algorithms[a], algorithm_b=algorithms[b],
                          **paired_test(differences), a_better=sum(d < 0 for d in differences),
                          ties=sum(d == 0 for d in differences), b_better=sum(d > 0 for d in differences),
                          median_rpd_difference_a_minus_b_pp=float(np.median([float(d) for d in differences]))))
    for pair, adjusted in zip(pairs, holm([pair['pvalue'] for pair in pairs])):
        pair['holm_pvalue'] = adjusted
        pair['significant_at_0_05'] = bool(omnibus['permutation_pvalue'] < ALPHA and adjusted < ALPHA)
    inputs = {name:hashlib.sha256((folder/name).read_bytes()).hexdigest()
              for name in ('runs.csv','protocol.json','metadata.json','audit.json')}
    result = dict(alpha=ALPHA, unit='One instance; mean over its 20 seeds for each algorithm',
                  instances=protocol['instances'], algorithms=algorithms, seeds_per_algorithm=len(protocol['seeds']),
                  metric='Mean RPD (% above BKS); Friedman ranks are equivalent to ranking mean makespan',
                  test_plan='Exploratory analysis after the benchmark results; all six two-sided pairs, Holm family-wise correction',
                  friedman=omnibus, mean_ranks=dict(zip(algorithms, map(float, ranks.mean(axis=0)))), posthoc=pairs,
                  wilcoxon_method='Exact sign permutations of nonzero paired RPD differences; average ranks for ties; zeros discarded',
                  assumptions='Instances treated as independent blocks; exchangeable algorithm labels under omnibus null; symmetric paired differences for Wilcoxon',
                  limitations=f"Selected instances from two families; {'pilot-selected settings' if protocol['parameter_overrides'] else 'untuned defaults'} and {protocol['budget']} evaluations; no universal algorithm claim; Monte Carlo omnibus p-value has finite resolution",
                  input_sha256=inputs, software=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__))
    (folder/'statistics.json').write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
    with (folder/'statistics-blocks.csv').open('w', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['instance'] + [alg+'_mean_rpd' for alg in algorithms] + [alg+'_rank' for alg in algorithms])
        for name, row, row_ranks in zip(protocol['instances'], rpds, ranks):
            writer.writerow([name] + [float(value) for value in row] + list(row_ranks))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main(Path(sys.argv[1]) if len(sys.argv)>1 else EXPERIMENT)
