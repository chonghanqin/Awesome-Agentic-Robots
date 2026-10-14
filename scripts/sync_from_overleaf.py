#!/usr/bin/env python3
"""Mirror active manuscript comparison tables; read Overleaf without writing it.

Run with --overleaf /path/to/overleaf. This checks the snapshot by default;
--write updates only this repository's data/papers.yaml and data/tables.yaml.
Unknown LaTeX display commands fail rather than silently losing content.
"""
import argparse
import hashlib
from html import escape, unescape
import json
from pathlib import Path
import re
import sys

import yaml

from validate import DOMAINS, ROOT, validate

GLYPHS = {'language': 'Text', 'image': 'Image', 'video': 'Video', 'geometry': '3D assets',
          'real': 'Real', 'sim': 'Sim', 'dataset': 'Offline data'}
ICONS = {'DataInputImage': 'Image', 'DataInputVideo': 'Video',
         'DataInputRobot': 'Robot data', 'DataInputCloud': 'Point cloud',
         'OrchPolicy': 'Learned policy', 'OrchTool': 'Analytic tool',
         'OrchSkill': 'Skill', 'OrchAgent': 'Other agent'}

# Versions used by the manuscript's evidence indexes (checked 2026-10-14).
# Some visible table links / bibliography titles still identify other versions.
ANALYZED_VERSIONS = {
    # data_comparison_index.json: Annotation source, sections 4.3–4.5 / 5.
    'survey_ax_2512_14442': ('https://arxiv.org/abs/2512.14442v1', None),
    # harness_literature_index.json: model_sources, section II-A.
    'survey_ax_2401_12202': ('https://arxiv.org/abs/2401.12202v2', None),
    # model_literature_index.json: paper_url and model_sources.
    'survey_ax_2609_01281': ('https://arxiv.org/abs/2609.01281v1', None),
    # harness_literature_index.json: analyzed_source explicitly identifies v2.
    'survey_ax_2609_20822': ('https://arxiv.org/abs/2609.20822v2',
                           'Coding Agents with Harness for Safe Robot Control'),
}


def argument(text, position, opening='{', closing='}'):
    while position < len(text) and text[position].isspace():
        position += 1
    if text[position:position+1] != opening:
        raise ValueError('Expected argument: ' + text[position:position+60])
    start = position + 1
    depth = 1
    position += 1
    while position < len(text):
        if text[position] == opening and (position == 0 or text[position-1] != '\\'):
            depth += 1
        elif text[position] == closing and text[position-1] != '\\':
            depth -= 1
            if not depth:
                return text[start:position], position + 1
        position += 1
    raise ValueError('Unclosed argument')


def display(text):
    """Translate display markup and legend-defined icons to safe readable HTML."""
    text = text.replace(r'$\pi^*_0.6$', 'π*₀.₆').replace(r'$\pi_0.5$', 'π₀.₅')
    out = []; i = 0
    while i < len(text):
        ch = text[i]
        if ch == '{':
            value, i = argument(text, i); out.append(display(value)); continue
        if ch in '}$':
            i += 1; continue
        if ch != '\\':
            out.append(escape(' ' if ch == '~' else ch)); i += 1; continue
        match = re.match(r'\\([A-Za-z]+|.)', text[i:])
        if not match:
            raise ValueError('Invalid display command')
        command = match[1]; i += len(match[0])
        if command in ('mbox', 'textbf', 'emph', 'textsuperscript'):
            value, i = argument(text, i)
            tag = {'textbf': 'strong', 'emph': 'em', 'textsuperscript': 'sup'}.get(command)
            out.append(('<'+tag+'>' if tag else '')+display(value)+('</'+tag+'>' if tag else ''))
        elif command == 'raisebox':
            _, i = argument(text, i); value, i = argument(text, i); out.append(display(value))
        elif command == 'includegraphics':
            if text[i:i+1] == '[': _, i = argument(text, i, '[', ']')
            value, i = argument(text, i)
            label = {'solid-robot.png': 'Real', 'solid-sim.png': 'Sim', 'solid-gen.png': 'Gen'}[Path(value).name]
            out.append(label)
        elif command in ('ComparisonGlyph', 'ComparisonInputSlot'):
            value, i = argument(text, i); out.append(GLYPHS[value]+' ')
        elif command in ICONS:
            if text[i:i+2] == '{}': i += 2
            out.append(ICONS[command]+' ')
        elif command == 'OrchHead':
            first, i = argument(text, i); second, i = argument(text, i)
            separator = ' ' if first and second and not first.endswith('-') else ''
            out.append(display(first+separator+second))
        elif command == 'Y': out.append('✅')
        elif command == 'N': out.append('❌')
        elif command == 'OrchExec':
            icons, i = argument(text, i); value, i = argument(text, i)
            out.append(display(icons).strip() + ': ' + display(value))
        elif command == 'hspace':
            _, i = argument(text, i); out.append(' / ')
        elif command in ('IcA', 'IcB', 'IcD'):
            pass  # The adjacent Before/During/After text carries the same meaning.
        elif command in ('PhA', 'PhB', 'PhD'):
            out.append({'PhA': 'After', 'PhB': 'Before', 'PhD': 'During'}[command])
        elif command in ('allowbreak', 'footnotesize'):
            if text[i:i+2] == '{}': i += 2
        elif command in ('enspace', ',', ';', ' '): out.append(' ')
        elif command in ('pi', 'zeta', 'sim', 'checkmark', 'textemdash'):
            out.append({'pi': 'π', 'zeta': 'ζ', 'sim': '≈', 'checkmark': '✓', 'textemdash': '—'}[command])
        elif command in ('&', '%', '_', '#'): out.append(escape(command))
        elif command == '-': pass
        else: raise ValueError('Unsupported display command: ' + command + ' in ' + text)
    return re.sub(r'\s+', ' ', ''.join(out)).replace('---', '—').replace('--', '–').strip()


def clean_source(path):
    return '\n'.join(re.split(r'(?<!\\)%', line, maxsplit=1)[0]
                     for line in path.read_text(encoding='utf-8').splitlines())


def table_from_tex(path, domain, category):
    source = clean_source(path)
    source = source[source.index(r'\begin{longtable}'):source.index(r'\end{longtable}')]
    caption_match = re.search(r'\\caption(?:\[[^\]]*\])?\s*', source)
    caption, _ = argument(source, caption_match.end())
    caption = re.sub(r'\s*\(Section~\\ref\{[^}]*\}\)', '', caption)
    caption = display(caption)
    # Caption legends already spell out each icon; remove its duplicate text label.
    for label in [*GLYPHS.values(), *ICONS.values(), 'Gen']:
        caption = re.sub(r'\b'+re.escape(label)+r'(?: /)?\s+'+re.escape(label)+r'\b', label, caption, flags=re.I)
    # Icon legends remain useful as text; link labels are explicit on GitHub.
    caption = caption.replace('Paper and GitHub icons link to the paper and repository', 'Paper and Code link to the paper and repository')
    caption = caption.replace('Icons in Link point to the paper and repository, respectively', 'Paper and Code link to the paper and repository')
    headers_line = next(line for line in source.splitlines() if '&' in line and 'Work' in line and 'Link' in line and 'textbf' in line)
    headers_line = re.sub(r'^\\rowcolor\{[^}]+\}', '', headers_line)
    headers = [re.sub('<[^>]+>', '', display(c)) for c in re.split(r'(?<!\\)&', re.split(r'\\\\', headers_line)[0])]
    n = len(headers)
    # Match manuscript widths when specified, with a shared fallback for natural-width tables.
    spec, _ = argument(source, len(r'\begin{longtable}'))
    widths = [float(w) for w in re.findall(r'p\{([.\d]+)\\LiteratureWidth\}', spec)]
    if len(widths) != n: widths = [.20, .10] + [.70/(n-2)]*(n-2)
    widths = [round(w/sum(widths)*100, 4) for w in widths]
    notes = []
    footer = source[source.index(r'\endfoot'):source.index(r'\endlastfoot')]
    for line in footer.splitlines():
        if 'footnotesize' in line:
            notes.append(display(re.search(r'\\footnotesize (.*)', line)[1].rsplit('}', 1)[0].rstrip('\\ ')))
    body = source.split(r'\endlastfoot', 1)[1]
    rows = []; group = None
    # TeX row terminators, rather than physical lines, also cover hand-edited multiline rows.
    for segment in re.split(r'\\\\\*?(?:\s*\[[^\]]*\])?', body):
        for line in segment.splitlines():
            if r'\MemGroup{' in line:
                group, _ = argument(line, line.index(r'\MemGroup')+len(r'\MemGroup'))
            if 'multicolumn' in line and 'textbf' in line and 'citep' not in line:
                position = line.index(r'\multicolumn')+len(r'\multicolumn')
                for _ in range(3): value, position = argument(line, position)
                group = re.sub('<[^>]+>', '', display(value))
        if r'\citep{' not in segment or '&' not in segment: continue
        # Discard rules and group commands preceding the work-name line.
        start = segment.rfind('\n', 0, segment.index(r'\citep{'))+1
        line = segment[start:].strip()
        cells = [c.strip() for c in re.split(r'(?<!\\)&', line)]
        if len(cells) != n: raise ValueError(f'{path.name}: {len(cells)} cells, expected {n}')
        key = re.search(r'\\citep\{([^}]+)\}', cells[0])[1]
        work = re.sub(r'\\mbox\{\\citep\{[^}]+\}\}|\\citep\{[^}]+\}', '', cells[0])
        link = re.search(r'\\LiteratureLinks(?:\[[^\]]*\])?\{([^}]+)\}\{([^}]*)\}', cells[1])
        if link: paper, code = link.groups()
        else:
            paper = re.search(r'\\LiteraturePaperLink\{([^}]+)\}', cells[1])[1]
            code_match = re.search(r'\\LiteratureCode\{([^}]+)\}', cells[1]); code = code_match[1] if code_match else None
        rows.append(dict(bibkey=key, work=display(work), paper=paper, code=code or None,
                         code_partial=r'\dagger' in cells[1], group=group, cells=[display(c) for c in cells[2:]]))
    if not rows: raise ValueError('Empty active table: ' + str(path))
    return dict(key=domain.lower()+'.'+category.lower().replace(' ', '_'), domain=domain,
                category=category, headers=headers, widths=widths, caption=caption, notes=notes, rows=rows)


def extract(source):
    source = source.resolve()
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source/'scripts'))
    from check_citation_hygiene import parse_bibliography
    from table_venues import literal
    bibliography = dict(parse_bibliography((source/'ref.bib').read_text()))
    switch = clean_source(source/'tables/comparison_draft_switch.tex')
    if not re.search(r'\\ComparisonDraftstrue\b', switch):
        raise ValueError('Expected active comparison drafts; inspect the current manuscript switch')
    tables=[]; papers={}; hashes={}
    paths=[source/'ref.bib', source/'main.tex', source/'tables/comparison_draft_switch.tex']
    for domain, categories in DOMAINS.items():
        chapter = source/('sections/'+domain.lower()+'.tex'); paths.append(chapter)
        chapter_text = clean_source(chapter)
        for category in categories:
            stem=domain.lower()+'_'+category.lower().replace(' ', '_')
            directive = (r'\input{tables/'+stem+'}') if domain=='Data' else (r'\ComparisonTable{'+stem+'}')
            direct_input = r'\input{tables/'+stem+'_draft}'
            if directive not in chapter_text and (domain=='Data' or direct_input not in chapter_text):
                raise ValueError('Inactive manuscript subsection: '+stem)
            path=source/('tables/'+stem+('' if domain=='Data' else '_draft')+'.tex');paths.append(path)
            table=table_from_tex(path,domain,category);tables.append(table)
            for row in table['rows']:
                key=row['bibkey']; fields=bibliography[key]
                analyzed = ANALYZED_VERSIONS.get(key)
                if analyzed: row['paper'] = analyzed[0]
                title=display(literal(fields['title']))
                title=unescape(re.sub('<[^>]+>','',title))
                if analyzed and analyzed[1]: title = analyzed[1]
                if key not in papers: papers[key]=dict(id=key,title=title,categories=[])
                if table['key'] not in papers[key]['categories']:papers[key]['categories'].append(table['key'])
    for path in paths:hashes[str(path.relative_to(source))]=hashlib.sha256(path.read_bytes()).hexdigest()
    return sorted(papers.values(),key=lambda p:p['id']),tables,hashes


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--overleaf',type=Path,required=True)
    parser.add_argument('--write',action='store_true')
    args=parser.parse_args()
    papers,tables,_=extract(args.overleaf)
    validate(papers, tables)
    for name,records in [('papers',papers),('tables',tables)]:
        path=ROOT/('data/'+name+'.yaml')
        content=yaml.safe_dump(records,allow_unicode=True,sort_keys=False,width=120)
        if args.write:path.write_text(content,encoding='utf-8')
        elif not path.exists() or path.read_text()!=content:raise SystemExit('Stale snapshot: '+str(path))
    print(json.dumps(dict(works=len(papers),tables=len(tables),rows=sum(len(t['rows']) for t in tables))))


if __name__=='__main__':main()
