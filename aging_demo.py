#!/usr/bin/env python3
"""Show starvation in priority scheduling and how aging helps."""

from sched import calculate_metrics, format_gantt, read_processes, simulate


def show(aging_interval: int) -> None:
    processes = read_processes("starvation.txt")
    intervals = simulate(processes, "priority", aging_interval=aging_interval)
    metrics = calculate_metrics(processes, intervals)
    low = metrics["per_process"]["LOW"]
    label = "without aging" if aging_interval == 0 else f"aging interval = {aging_interval}"
    print(f"\n{label}")
    print(f"LOW waiting={low['waiting']}, response={low['response']}, completion={low['completion']}")
    print(format_gantt(intervals))


def main() -> int:
    show(0)
    show(1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
