#!/usr/bin/env python3
"""CPU scheduling simulator: FCFS, SJF, SRTF, preemptive Priority and RR."""

from __future__ import annotations

import argparse
from collections import deque
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple


@dataclass(frozen=True)
class Process:
    pid: str
    arrival: int
    burst: int
    priority: int = 0
    order: int = 0


@dataclass(frozen=True)
class Interval:
    start: int
    end: int
    pid: Optional[str]


def read_processes(path: str | Path) -> List[Process]:
    """Read PID arrival burst [priority] rows from a text file."""
    processes: List[Process] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line_no, raw in enumerate(fh, 1):
            line = raw.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) not in (3, 4):
                raise ValueError(f"{path}:{line_no}: expected 'PID arrival burst [priority]'")
            pid = parts[0]
            try:
                arrival = int(parts[1])
                burst = int(parts[2])
                priority = int(parts[3]) if len(parts) == 4 else 0
            except ValueError as exc:
                raise ValueError(f"{path}:{line_no}: numeric fields must be integers") from exc
            if arrival < 0:
                raise ValueError(f"{path}:{line_no}: arrival must be >= 0")
            if burst <= 0:
                raise ValueError(f"{path}:{line_no}: burst must be > 0")
            processes.append(Process(pid, arrival, burst, priority, len(processes)))
    if not processes:
        raise ValueError(f"{path}: no processes found")
    if len({p.pid for p in processes}) != len(processes):
        raise ValueError(f"{path}: PID values must be unique")
    return processes


def _append_interval(intervals: List[Interval], start: int, end: int, pid: Optional[str]) -> None:
    if start >= end:
        return
    if intervals and intervals[-1].pid == pid and intervals[-1].end == start:
        prev = intervals[-1]
        intervals[-1] = Interval(prev.start, end, pid)
    else:
        intervals.append(Interval(start, end, pid))


def _validate(processes: Sequence[Process]) -> None:
    if not processes:
        raise ValueError("process list must not be empty")
    if len({p.pid for p in processes}) != len(processes):
        raise ValueError("PID values must be unique")
    for p in processes:
        if p.arrival < 0 or p.burst <= 0:
            raise ValueError("arrival must be >= 0 and burst must be > 0")


def simulate(processes: Sequence[Process], algorithm: str, **params: int) -> List[Interval]:
    """Simulate one scheduler and return execution intervals.

    Supported algorithms: fcfs, sjf, srtf, priority, rr.
    Smaller numeric priority means higher priority.
    aging_interval=0 disables aging.

    RR convention: arrivals at time t enter the queue before a process whose
    quantum expires at exactly the same time t is re-enqueued.
    """
    _validate(processes)
    algo = algorithm.lower()
    if algo not in {"fcfs", "sjf", "srtf", "priority", "rr"}:
        raise ValueError(f"unknown algorithm: {algorithm}")

    procs = sorted(processes, key=lambda p: (p.arrival, p.order))
    if algo == "rr":
        quantum = int(params.get("quantum", 0))
        if quantum <= 0:
            raise ValueError("RR requires quantum > 0")
        return _simulate_rr(procs, quantum)
    if algo in {"fcfs", "sjf"}:
        return _simulate_nonpreemptive(procs, algo)
    if algo == "srtf":
        return _simulate_srtf(procs)

    aging_interval = int(params.get("aging_interval", 0))
    if aging_interval < 0:
        raise ValueError("aging_interval must be >= 0")
    return _simulate_priority(procs, aging_interval)


def _simulate_nonpreemptive(procs: Sequence[Process], algo: str) -> List[Interval]:
    t = 0
    done = 0
    n = len(procs)
    ready: List[Process] = []
    next_idx = 0
    intervals: List[Interval] = []

    while done < n:
        while next_idx < n and procs[next_idx].arrival <= t:
            ready.append(procs[next_idx])
            next_idx += 1

        if not ready:
            next_t = procs[next_idx].arrival
            _append_interval(intervals, t, next_t, None)
            t = next_t
            continue

        if algo == "fcfs":
            chosen_idx = min(range(len(ready)), key=lambda i: (ready[i].arrival, ready[i].order))
        else:
            chosen_idx = min(
                range(len(ready)),
                key=lambda i: (ready[i].burst, ready[i].arrival, ready[i].order),
            )
        p = ready.pop(chosen_idx)
        _append_interval(intervals, t, t + p.burst, p.pid)
        t += p.burst
        done += 1

    return intervals


def _simulate_srtf(procs: Sequence[Process]) -> List[Interval]:
    remaining: Dict[str, int] = {p.pid: p.burst for p in procs}
    intervals: List[Interval] = []
    t = 0
    completed = 0
    n = len(procs)

    while completed < n:
        ready = [p for p in procs if p.arrival <= t and remaining[p.pid] > 0]
        if not ready:
            future = [p.arrival for p in procs if remaining[p.pid] > 0 and p.arrival > t]
            next_t = min(future)
            _append_interval(intervals, t, next_t, None)
            t = next_t
            continue

        p = min(ready, key=lambda x: (remaining[x.pid], x.arrival, x.order))
        _append_interval(intervals, t, t + 1, p.pid)
        remaining[p.pid] -= 1
        t += 1
        if remaining[p.pid] == 0:
            completed += 1

    return intervals


def _simulate_priority(procs: Sequence[Process], aging_interval: int) -> List[Interval]:
    remaining: Dict[str, int] = {p.pid: p.burst for p in procs}
    waited: Dict[str, int] = {p.pid: 0 for p in procs}
    intervals: List[Interval] = []
    t = 0
    completed = 0
    n = len(procs)

    while completed < n:
        ready = [p for p in procs if p.arrival <= t and remaining[p.pid] > 0]
        if not ready:
            future = [p.arrival for p in procs if remaining[p.pid] > 0 and p.arrival > t]
            next_t = min(future)
            _append_interval(intervals, t, next_t, None)
            t = next_t
            continue

        def effective_priority(p: Process) -> int:
            improvement = waited[p.pid] // aging_interval if aging_interval > 0 else 0
            return p.priority - improvement

        p = min(ready, key=lambda x: (effective_priority(x), x.arrival, x.order))
        for other in ready:
            if other.pid != p.pid:
                waited[other.pid] += 1

        _append_interval(intervals, t, t + 1, p.pid)
        remaining[p.pid] -= 1
        t += 1
        if remaining[p.pid] == 0:
            completed += 1

    return intervals


def _simulate_rr(procs: Sequence[Process], quantum: int) -> List[Interval]:
    intervals: List[Interval] = []
    remaining: Dict[str, int] = {p.pid: p.burst for p in procs}
    ready: deque[Process] = deque()
    t = 0
    next_idx = 0
    completed = 0
    n = len(procs)

    while completed < n:
        while next_idx < n and procs[next_idx].arrival <= t:
            ready.append(procs[next_idx])
            next_idx += 1

        if not ready:
            next_t = procs[next_idx].arrival
            _append_interval(intervals, t, next_t, None)
            t = next_t
            continue

        p = ready.popleft()
        run = min(quantum, remaining[p.pid])
        for _ in range(run):
            _append_interval(intervals, t, t + 1, p.pid)
            remaining[p.pid] -= 1
            t += 1

            # Arrival-before-requeue rule from the assignment.
            while next_idx < n and procs[next_idx].arrival <= t:
                ready.append(procs[next_idx])
                next_idx += 1
            if remaining[p.pid] == 0:
                break

        if remaining[p.pid] == 0:
            completed += 1
        else:
            ready.append(p)

    return intervals


def calculate_metrics(processes: Sequence[Process], intervals: Sequence[Interval]) -> Dict[str, object]:
    first_start: Dict[str, int] = {}
    completion: Dict[str, int] = {}
    busy = 0

    for item in intervals:
        if item.pid is None:
            continue
        busy += item.end - item.start
        first_start.setdefault(item.pid, item.start)
        completion[item.pid] = item.end

    per_process: Dict[str, Dict[str, int]] = {}
    waits: List[int] = []
    turnarounds: List[int] = []
    responses: List[int] = []

    for p in processes:
        if p.pid not in completion:
            raise ValueError(f"process {p.pid} did not complete")
        turnaround = completion[p.pid] - p.arrival
        waiting = turnaround - p.burst
        response = first_start[p.pid] - p.arrival
        per_process[p.pid] = {
            "waiting": waiting,
            "turnaround": turnaround,
            "response": response,
            "completion": completion[p.pid],
        }
        waits.append(waiting)
        turnarounds.append(turnaround)
        responses.append(response)

    finish_time = max(completion.values())
    elapsed = finish_time
    utilization = 100.0 * busy / elapsed if elapsed else 0.0

    return {
        "avg_waiting": sum(waits) / len(waits),
        "avg_turnaround": sum(turnarounds) / len(turnarounds),
        "avg_response": sum(responses) / len(responses),
        "cpu_utilization": utilization,
        "per_process": per_process,
    }


def context_switches(intervals: Sequence[Interval]) -> int:
    switches = 0
    previous: Optional[str] = None
    for item in intervals:
        if item.pid is None:
            previous = None
            continue
        if previous is not None and item.pid != previous:
            switches += 1
        previous = item.pid
    return switches


def format_gantt(intervals: Sequence[Interval]) -> str:
    return " | ".join(f"{x.start}-{x.end}:{x.pid if x.pid is not None else 'IDLE'}" for x in intervals)


def _print_metrics_table(rows: Sequence[Tuple[str, Dict[str, object], int]]) -> None:
    headers = ("Algorithm", "Avg wait", "Avg turnaround", "Avg response", "CPU util", "Switches")
    formatted = []
    for name, metrics, switches in rows:
        formatted.append((
            name,
            f"{metrics['avg_waiting']:.2f}",
            f"{metrics['avg_turnaround']:.2f}",
            f"{metrics['avg_response']:.2f}",
            f"{metrics['cpu_utilization']:.2f}%",
            str(switches),
        ))
    widths = [max(len(headers[i]), *(len(row[i]) for row in formatted)) for i in range(len(headers))]
    print("  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))))
    print("  ".join("-" * widths[i] for i in range(len(headers))))
    for row in formatted:
        print("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="CPU scheduling simulator")
    parser.add_argument("file", help="input file: PID arrival burst [priority]")
    parser.add_argument("--algo", required=True, choices=["fcfs", "sjf", "srtf", "priority", "rr", "all"])
    parser.add_argument("--quantum", type=int, default=3, help="RR quantum (default: 3)")
    parser.add_argument("--aging-interval", type=int, default=0, help="priority aging interval; 0 disables aging")
    parser.add_argument("--gantt", action="store_true", help="print execution intervals")
    args = parser.parse_args(argv)

    processes = read_processes(args.file)
    algos = ["fcfs", "sjf", "srtf", "priority", "rr"] if args.algo == "all" else [args.algo]
    rows = []
    gantts: List[Tuple[str, List[Interval]]] = []

    for algo in algos:
        params: Dict[str, int] = {}
        if algo == "rr":
            params["quantum"] = args.quantum
        if algo == "priority":
            params["aging_interval"] = args.aging_interval
        intervals = simulate(processes, algo, **params)
        metrics = calculate_metrics(processes, intervals)
        label = algo.upper()
        if algo == "rr":
            label += f"(q={args.quantum})"
        if algo == "priority" and args.aging_interval:
            label += f"(aging={args.aging_interval})"
        rows.append((label, metrics, context_switches(intervals)))
        gantts.append((label, intervals))

    _print_metrics_table(rows)
    if args.gantt:
        print()
        for label, intervals in gantts:
            print(f"{label}: {format_gantt(intervals)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
