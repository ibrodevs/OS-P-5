#!/usr/bin/env python3
"""Analyze RR quantum 1..10 on set2 and write an SVG graph."""

from __future__ import annotations

import argparse
from pathlib import Path
from sched import calculate_metrics, context_switches, read_processes, simulate


def build_rows(path: str):
    processes = read_processes(path)
    rows = []
    for q in range(1, 11):
        intervals = simulate(processes, "rr", quantum=q)
        metrics = calculate_metrics(processes, intervals)
        rows.append((q, float(metrics["avg_waiting"]), context_switches(intervals)))
    return rows


def write_svg(rows, output: str) -> None:
    width, height = 900, 500
    left, right, top, bottom = 80, 80, 55, 70
    plot_w = width - left - right
    plot_h = height - top - bottom
    max_wait = max(r[1] for r in rows) * 1.08
    max_switch = max(r[2] for r in rows) * 1.08

    def x(q):
        return left + (q - 1) / 9 * plot_w

    def y_wait(v):
        return top + plot_h - (v / max_wait) * plot_h

    def y_switch(v):
        return top + plot_h - (v / max_switch) * plot_h

    wait_points = " ".join(f"{x(q):.1f},{y_wait(w):.1f}" for q, w, _ in rows)
    switch_points = " ".join(f"{x(q):.1f},{y_switch(s):.1f}" for q, _, s in rows)

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<style>text{font-family:Arial,sans-serif;font-size:13px}.title{font-size:20px;font-weight:bold}.axis{stroke:#222;stroke-width:1}.grid{stroke:#ddd;stroke-width:1}.wait{stroke:#1565c0;fill:none;stroke-width:3}.switch{stroke:#c62828;fill:none;stroke-width:3}</style>',
        f'<text x="{width/2}" y="28" text-anchor="middle" class="title">RR on set2: quantum vs waiting time / context switches</text>',
        f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top+plot_h}" class="axis"/>',
        f'<line x1="{left}" y1="{top+plot_h}" x2="{left+plot_w}" y2="{top+plot_h}" class="axis"/>',
        f'<line x1="{left+plot_w}" y1="{top}" x2="{left+plot_w}" y2="{top+plot_h}" class="axis"/>',
    ]

    for i in range(6):
        frac = i / 5
        yy = top + plot_h - frac * plot_h
        wv = frac * max_wait
        sv = frac * max_switch
        parts.append(f'<line x1="{left}" y1="{yy:.1f}" x2="{left+plot_w}" y2="{yy:.1f}" class="grid"/>')
        parts.append(f'<text x="{left-10}" y="{yy+4:.1f}" text-anchor="end">{wv:.1f}</text>')
        parts.append(f'<text x="{left+plot_w+10}" y="{yy+4:.1f}" text-anchor="start">{sv:.0f}</text>')

    for q, _, _ in rows:
        xx = x(q)
        parts.append(f'<line x1="{xx:.1f}" y1="{top+plot_h}" x2="{xx:.1f}" y2="{top+plot_h+5}" class="axis"/>')
        parts.append(f'<text x="{xx:.1f}" y="{top+plot_h+23}" text-anchor="middle">{q}</text>')

    parts += [
        f'<polyline points="{wait_points}" class="wait"/>',
        f'<polyline points="{switch_points}" class="switch"/>',
        f'<text x="{left+plot_w/2}" y="{height-18}" text-anchor="middle">Quantum</text>',
        f'<text x="18" y="{top+plot_h/2}" transform="rotate(-90 18 {top+plot_h/2})" text-anchor="middle">Average waiting time</text>',
        f'<text x="{width-18}" y="{top+plot_h/2}" transform="rotate(90 {width-18} {top+plot_h/2})" text-anchor="middle">Context switches</text>',
        f'<line x1="{left+10}" y1="{top+15}" x2="{left+40}" y2="{top+15}" class="wait"/><text x="{left+48}" y="{top+20}">avg waiting</text>',
        f'<line x1="{left+160}" y1="{top+15}" x2="{left+190}" y2="{top+15}" class="switch"/><text x="{left+198}" y="{top+20}">context switches</text>',
        '</svg>',
    ]
    Path(output).write_text("\n".join(parts), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", nargs="?", default="set2.txt")
    parser.add_argument("--svg", default="rr_quantum.svg")
    args = parser.parse_args()

    rows = build_rows(args.file)
    print("q  avg_waiting  switches")
    print("-- -----------  --------")
    for q, wait, switches in rows:
        print(f"{q:2d} {wait:11.2f}  {switches:8d}")
    write_svg(rows, args.svg)
    print(f"\nSVG graph written to {args.svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
