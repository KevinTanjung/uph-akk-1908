"""Classical JSSP model and common decoder (proposal III–IV)."""
from __future__ import annotations
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Instance:
    name: str
    machines: int
    jobs: tuple
    bks: int | None = None
    source: str = 'user supplied'

    def __post_init__(self):
        integer = lambda x: type(x) is int
        if not self.name or not integer(self.machines) or self.machines < 1 or not self.jobs:
            raise ValueError('name, positive machine count and nonempty jobs required')
        for job in self.jobs:
            if not job:
                raise ValueError('empty job')
            for machine, duration in job:
                if not integer(machine) or not 0 <= machine < self.machines:
                    raise ValueError('machine index out of range')
                if not integer(duration) or duration <= 0:
                    raise ValueError('duration must be a positive integer')
        if self.bks is not None and (not integer(self.bks) or self.bks <= 0):
            raise ValueError('bks must be positive')

    @property
    def sequence(self):
        return [j for j, job in enumerate(self.jobs) for _ in job]

    @property
    def lower_bound(self):
        return max(max(sum(p for _, p in job) for job in self.jobs),
                   max(sum(p for job in self.jobs for m, p in job if m == machine)
                       for machine in range(self.machines)))


def load(path):
    data = json.loads(Path(path).read_text())
    return Instance(data['name'], data['machines'],
                    tuple(tuple(tuple(op) for op in job) for job in data['jobs']),
                    data.get('bks'), data.get('source', 'user supplied'))


def decode(instance, sequence):
    """Each job occurrence selects its next operation; insert in first fitting gap."""
    if any(type(j) is not int for j in sequence) or Counter(sequence) != Counter(instance.sequence):
        raise ValueError('sequence must contain each job once per operation')
    next_op = [0] * len(instance.jobs)
    ready = [0] * len(instance.jobs)
    calendars = [[] for _ in range(instance.machines)]
    schedule = []
    for j in sequence:
        k = next_op[j]
        machine, duration = instance.jobs[j][k]
        start = ready[j]
        for left, right in sorted(calendars[machine]):
            if start + duration <= left:
                break
            start = max(start, right)
        end = start + duration
        calendars[machine].append((start, end))
        schedule.append(dict(job=j, operation=k, machine=machine, start=start, end=end))
        next_op[j] += 1
        ready[j] = end
    return max(ready), schedule


def validate(instance, schedule):
    expected = {(j, k) for j, job in enumerate(instance.jobs) for k in range(len(job))}
    indexed = {(op['job'], op['operation']): op for op in schedule}
    if len(schedule) != len(expected) or set(indexed) != expected:
        raise ValueError('missing or duplicate operations')
    for (j, k), op in indexed.items():
        m, p = instance.jobs[j][k]
        if op['machine'] != m or type(op['start']) is not int or op['start'] < 0 or op['end'] != op['start'] + p:
            raise ValueError('invalid operation timing or machine')
        if k and indexed[j, k-1]['end'] > op['start']:
            raise ValueError('job precedence violated')
    for m in range(instance.machines):
        ops = sorted((op for op in schedule if op['machine'] == m), key=lambda op: op['start'])
        if any(a['end'] > b['start'] for a, b in zip(ops, ops[1:])):
            raise ValueError('machine overlap')
    return True


def spt(instance):
    next_op = [0] * len(instance.jobs)
    sequence = []
    while len(sequence) < len(instance.sequence):
        j = min((j for j, job in enumerate(instance.jobs) if next_op[j] < len(job)),
                key=lambda j: (instance.jobs[j][next_op[j]][1], j))
        sequence.append(j)
        next_op[j] += 1
    return sequence


def load_orlib(path, name):
    """Read a named instance from the OR-Library jobshop1 text format."""
    lines = Path(path).read_text().splitlines()
    marker = 'instance ' + name
    for i, line in enumerate(lines):
        if line.strip() == marker:
            for h in range(i + 1, len(lines)):
                fields = lines[h].split()
                if len(fields) == 2 and all(x.isdigit() for x in fields):
                    n, m = map(int, fields)
                    rows = [list(map(int, row.split())) for row in lines[h+1:h+1+n]]
                    if len(rows) != n or any(len(row) != 2*m for row in rows):
                        raise ValueError('incomplete OR-Library instance')
                    return Instance(name, m, tuple(tuple(zip(row[::2], row[1::2])) for row in rows),
                                    source='OR-Library jobshop1; BKS not supplied')
    raise ValueError('instance not found: ' + name)
