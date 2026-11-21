"""Offline HTML report, refreshed during a run without external libraries."""
import html
from pathlib import Path

COLORS = ['#0072b2','#d55e00','#009e73','#cc79a7','#e69f00','#56b4e9']


def write_report(path, runs, running=False):
    esc = lambda value: html.escape(str(value))
    parts = ['<!doctype html><html lang="en"><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>JSSP simulation</title>',
             '<style>body{font:16px system-ui;max-width:1150px;margin:30px auto;padding:0 20px;color:#182532;background:#f7f9fb}svg{width:100%;height:auto;background:white;border:1px solid #ccd4dd}table{border-collapse:collapse;width:100%;background:white}th,td{padding:8px;text-align:left;border-bottom:1px solid #ddd}section{margin:35px 0}text{font:12px system-ui}a{color:#005e95}</style>',
             '<h1>Job-shop scheduling simulation</h1>',
             '<p>Lower makespan is better. Time units come from the input data. Each evaluation measures one candidate schedule.</p>']
    if running:
        parts += ['<meta http-equiv="refresh" content="2"><p role="status">Running · refreshes every two seconds. Partial results below.</p>']
    else:
        parts += ['<p>Run finished. See failures.jsonl for any failed runs. Synthetic cases are software tests, not public benchmarks.</p>']
    parts += ['<h2>Run results</h2><table><tr><th>Instance</th><th>Algorithm</th><th>Seed</th><th>Makespan</th><th>RPD %</th><th>Seconds</th><th>Evaluations</th></tr>']
    for r in runs:
        parts.append('<tr>'+''.join('<td>'+esc(v)+'</td>' for v in [r['instance'],r['algorithm'],r['seed'],r['makespan'],'' if r['rpd'] is None else round(r['rpd'],2),round(r['runtime_seconds'],4),len(r['history'])])+'</tr>')
    parts.append('</table>')
    for r in runs:
        label=f"{r['instance']} / {r['algorithm'].upper()} / seed {r['seed']}"
        history=r['history']
        maximum=max(row['current'] for row in history)
        width,height=1050,250
        points=lambda key:' '.join(f"{60+940*(row['evaluation']-1)/max(1,r['budget']-1):.1f},{210-170*row[key]/maximum:.1f}" for row in history)
        parts += ['<section><h2>'+esc(label)+'</h2>',
                  '<h3>Search progress</h3><p>Horizontal: candidate evaluations. Vertical: makespan. Gray: current candidate. Blue: best found.</p>',
                  f'<svg viewBox="0 0 {width} {height}" role="img" aria-label="{esc(label)} convergence"><title>{esc(label)} convergence</title>',
                  '<path d="M60 30V210H1000" fill="none" stroke="#445"/>',
                  f'<text x="5" y="40">{maximum}</text><text x="30" y="215">0</text><text x="60" y="235">1</text><text x="940" y="235">{r["budget"]}</text>',
                  f'<polyline points="{points("current")}" fill="none" stroke="#abb3bd"/><polyline points="{points("best")}" fill="none" stroke="#0072b2" stroke-width="2"/></svg>',
                  '<h3>Best schedule</h3><p>Rows are machines; labels identify job and operation (both start at 0).</p>']
        rows=max(op['machine'] for op in r['schedule'])+1
        parts += [f'<svg viewBox="0 0 1050 {60+rows*40}" role="img" aria-label="{esc(label)} machine schedule"><title>{esc(label)} Gantt chart</title>']
        for m in range(rows): parts.append(f'<text x="5" y="{50+m*40}">M{m}</text>')
        for op in r['schedule']:
            x=60+940*op['start']/r['makespan'];w=940*(op['end']-op['start'])/r['makespan'];y=30+op['machine']*40
            title=f"J{op['job']} O{op['operation']}: {op['start']}–{op['end']}"
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="30" fill="{COLORS[op["job"]%len(COLORS)]}"><title>{title}</title></rect>')
            if w>45: parts.append(f'<text x="{x+3}" y="{y+20}" fill="white">J{op["job"]}.{op["operation"]}</text>')
        parts += [f'<text x="60" y="{rows*40+50}">0</text><text x="950" y="{rows*40+50}">{r["makespan"]}</text></svg>',
                  '<details><summary>Schedule values</summary><table><tr><th>Job</th><th>Operation</th><th>Machine</th><th>Start</th><th>End</th></tr>']
        for op in r['schedule']: parts.append('<tr>'+''.join(f'<td>{op[k]}</td>' for k in ('job','operation','machine','start','end'))+'</tr>')
        parts += ['</table></details></section>']
    parts.append('</html>')
    target=Path(path);temporary=target.with_suffix('.tmp');temporary.write_text('\n'.join(parts));temporary.replace(target)
