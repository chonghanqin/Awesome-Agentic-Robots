#!/usr/bin/env python3
"""Render a paper list with full titles, concise summaries and source links."""
from html import escape, unescape
from urllib.parse import quote
import re

from validate import DOMAINS, ROOT, load_papers, load_tables, validate

BEGIN = '<!-- BEGIN AUTO-GENERATED PAPER LIST -->'
END = '<!-- END AUTO-GENERATED PAPER LIST -->'


def link(label, url):
    target = escape(quote(url, safe=':/?#=&%+@~.-_'), quote=True)
    return f'<a href="{target}">{label}</a>'


def icon_link(label, name, url):
    icon = (f'<picture><source media="(prefers-color-scheme: dark)" '
            f'srcset="assets/icons/{name}-dark.svg">'
            f'<img src="assets/icons/{name}.svg" width="18" height="18" '
            f'alt="{label}" title="{label}"></picture>')
    return link(icon, url)


def plain(value):
    return unescape(re.sub(r'<[^>]+>', '', value))


def summary(table, rows):
    """Describe the method focus using the manuscript's checked comparison cells."""
    columns = table['headers'][2:]
    values = {h: list(dict.fromkeys(plain(r['cells'][i]) for r in rows))
              for i,h in enumerate(columns)}
    # Normalize common comparison tags for sentence-style summaries; retain model names.
    common = {'Action','Actions','Adaptation','Camera','Collected','Constraint','Context','Control',
              'Corrections','Cost','Curriculum','Data','Demonstrations','Episode','Event',
              'Examples','Execution','Experience','Feedback','Functions','Generation','Goal',
              'Graph','Image','Input','Instructions','Interpreter','Labeling','Language',
              'Learned','Learning','Manipulation','Memory','Model','Motion','Navigation',
              'Object','Optimizer','Outcomes','Output','Perception','Plan','Planner','Plans',
              'Policy','Program','Query','Recovery','Reflection','Reinforcement','Replan',
              'Residual','Retrieval','Reward','Rewards','Robot','Scene','Selection','Signal',
              'Skill','Skills','State','Step','Structured','Supervised','Task','Tool','Training',
              'Update','Vision','Visual','Weights'}
    def field(name):
        value = '; '.join(v for v in values[name] if v)
        if name == 'Model': return value
        return re.sub(r'\b[A-Z][A-Za-z]+\b',
                      lambda m: m[0].lower() if m[0] in common else m[0], value)
    key = table['key']
    if key == 'model.training':
        text = f"{field('Approach')} for {field('Target')}"
    elif key == 'model.perception':
        text = f"{field('Perception process')} to produce {field('Output')}"
    elif key == 'model.planning':
        text = f"{field('Task')} planning with {field('Model')}; outputs {field('Plan Output')}"
    elif key == 'model.robot_control':
        text = f"Control interface: {field('Control Output')}; executor: {field('Executor')}; feedback: {field('Feedback')}"
    elif key == 'model.adaptation':
        text = f"{field('Adaptation Method')} for {field('Adapted Component')}; signals: {field('Adaptation Signal')}"
    elif key == 'data.collection':
        text = f"{field('Type')} collection of {field('Collected data')}; {field('Reported scale')}"
    elif key == 'data.annotation':
        outputs = list(dict.fromkeys(v.strip() for v in field('Output').split(';')))
        text = 'Data annotation for '+ '; '.join(outputs)
    elif key == 'data.refinement':
        text = f"Refines {field('Refinement Target')} with {field('Model')}"
    elif key == 'environment.reconstruction':
        text = f"Constructs {field('Representation')}; operations: {field('Agent Operations')}"
    elif key == 'environment.task_generation':
        text = f"Generates {field('Output')} from {field('Input')}"
    elif key == 'environment.benchmarking':
        text = f"Evaluation setting: {field('Setting')}; focus: {field('Capability')}"
    elif key == 'harness.orchestration':
        labels = {'Policy':'robot policies','Tool':'tools','Skill':'skills','Other Agent':'other agents'}
        executors = [label for h,label in labels.items() if '✅' in values[h]]
        text = field('Selection')+' selection of '+', '.join(executors)
    elif key == 'harness.memory':
        text = f"{field('Stored as')} memory; writes: {field('Written at')}; retrieval: {field('Retrieved by')}"
    elif key == 'harness.monitoring_and_recovery':
        text = f"Checks {field('Signal')} using {field('Checker')}; response: {field('Response')}"
    elif key == 'harness.skills':
        text = f"Reusable {field('Skill form')}; {field('Update')}"
    elif key == 'harness.infrastructure':
        text = f"{field('Purpose')}: {field('Main operation')}"
    elif key == 'harness.layered_systems':
        text = f"{field('Upper layer')} → {field('Lower layer')}; passes {field('Passed down')}"
    else: raise ValueError('Missing summary rule: '+key)
    text = text[0].upper()+text[1:]
    return text.rstrip('. ') + '.'


def listing_rows(table):
    # Annotation output groups can repeat a work; combine its summary once per category.
    grouped = {}
    for row in table['rows']:
        grouped.setdefault(row['bibkey'], []).append(row)
    return list(grouped.values())


def table_lines(table, papers):
    lines = ['<table width="100%">', '<thead><tr>',
             '<th width="60%" align="left">Paper Title</th>',
             '<th width="29%" align="left">Summary</th>',
             '<th width="11%" align="center" nowrap>Links</th>',
             '</tr></thead>', '<tbody>']
    for rows in listing_rows(table):
        row = rows[0]
        # Prefer a recorded code link if another annotation group supplies it.
        codes = {r['code'] for r in rows if r['code']}
        if len(codes) > 1: raise ValueError('Conflicting code links: '+row['bibkey'])
        code = next(iter(codes), None)
        title = link(escape(papers[row['bibkey']]['title']), row['paper'])
        links = icon_link('Paper', 'paper', row['paper']) + '&nbsp;&nbsp;'
        links += icon_link('GitHub repository', 'github', code) if code else '—'
        if any(r['code_partial'] for r in rows): links += '<sup>†</sup>'
        lines.append('<tr><td>'+title+'</td><td>'+escape(summary(table,rows))+
                     '</td><td align="center" nowrap>'+links+'</td></tr>')
    lines += ['</tbody>', '</table>']
    if any(row['code_partial'] for row in table['rows']):
        lines += ['<p><sup>†</sup> Partial code release.</p>']
    return lines


def render(papers, tables):
    validate(papers,tables); lookup = {p['id']:p for p in papers}; lines=[]
    for domain in DOMAINS:
        lines += [f'### {domain}', '']
        for table in tables:
            if table['domain'] == domain:
                anchor = table['category'].lower().replace(' ', '-')
                lines += [f'<a id="{anchor}"></a>', '',
                          f'#### {domain} · {table["category"]}', '', *table_lines(table,lookup), '']
    return '\n'.join(lines)


def updated_readme(readme, papers, tables):
    if readme.count(BEGIN) != 1 or readme.count(END) != 1 or readme.index(BEGIN) >= readme.index(END):
        raise ValueError('README must contain one ordered generation marker pair')
    before, rest = readme.split(BEGIN,1); _,after = rest.split(END,1)
    return before+BEGIN+'\n\n'+render(papers,tables)+'\n'+END+after


def main():
    path=ROOT/'README.md'
    path.write_text(updated_readme(path.read_text(encoding='utf-8'),load_papers(),load_tables()),encoding='utf-8')
    print('Updated paper lists.')


if __name__ == '__main__': main()
