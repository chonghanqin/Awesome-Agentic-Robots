#!/usr/bin/env python3
"""Render a paper list with full titles and source links."""
import re
from hashlib import sha256
from html import escape
from urllib.parse import quote

from validate import DOMAINS, ROOT, load_papers, load_tables, validate

BEGIN = '<!-- BEGIN AUTO-GENERATED PAPER LIST -->'
END = '<!-- END AUTO-GENERATED PAPER LIST -->'


def figure_src(name):
    path = f'assets/figures/{name}.webp'
    version = sha256((ROOT / path).read_bytes()).hexdigest()[:12]
    return ('https://raw.githubusercontent.com/chonghanqin/'
            f'Awesome-Agentic-Robots/main/{path}?v={version}')


def link(label, url):
    target = escape(quote(url, safe=':/?#=&%+@~.-_'), quote=True)
    return f'<a href="{target}">{label}</a>'


def icon_link(label, name, url):
    icon = (f'<picture><source media="(prefers-color-scheme: dark)" '
            f'srcset="assets/icons/{name}-dark.svg">'
            f'<img src="assets/icons/{name}.svg" width="18" height="18" '
            f'alt="{label}" title="{label}"></picture>')
    return link(icon, url)


def listing_rows(table):
    # Annotation output groups can repeat a work; list each work once per category.
    grouped = {}
    for row in table['rows']:
        grouped.setdefault(row['bibkey'], []).append(row)
    return list(grouped.values())


def table_lines(table, papers):
    lines = ['<table width="100%">', '<thead><tr>',
             '<th width="89%" align="left">Paper Title</th>',
             '<th width="11%" align="center" nowrap>Code</th>',
             '</tr></thead>', '<tbody>']
    for rows in listing_rows(table):
        row = rows[0]
        # Prefer a recorded code link if another annotation group supplies it.
        codes = {r['code'] for r in rows if r['code']}
        if len(codes) > 1: raise ValueError('Conflicting code links: '+row['bibkey'])
        code = next(iter(codes), None)
        title = link(escape(papers[row['bibkey']]['title']), row['paper'])
        links = icon_link('GitHub repository', 'github', code) if code else '—'
        if any(r['code_partial'] for r in rows): links += '<sup>†</sup>'
        lines.append('<tr><td>'+title+'</td><td align="center" nowrap>'+links+'</td></tr>')
    lines += ['</tbody>', '</table>']
    if any(row['code_partial'] for row in table['rows']):
        lines += ['<p><sup>†</sup> Partial code release.</p>']
    return lines


def render(papers, tables):
    validate(papers,tables); lookup = {p['id']:p for p in papers}; lines=[]
    for domain in DOMAINS:
        navigation = ' · '.join(link(escape(category), '#'+category.lower().replace(' ', '-'))
                                for category in DOMAINS[domain])
        lines += [f'### {domain}', '', f'<p>{navigation}</p>', '',
                  '<details open>', f'<summary>{domain} overview figure</summary>', '',
                  f'<p><a href="assets/figures/{domain.lower()}.png">'
                  f'<img src="{figure_src(domain.lower())}" '
                  f'alt="{domain} in agentic robotics" width="100%"></a></p>', '',
                  '</details>', '']
        for table in tables:
            if table['domain'] == domain:
                anchor = table['category'].lower().replace(' ', '-')
                lines += [f'<a id="{anchor}"></a>', '',
                          f'#### {domain} · {table["category"]}', '', *table_lines(table,lookup), '']
        lines += ['<p align="right"><a href="#taxonomy">↑ Back to contents</a></p>', '', '---', '']
    return '\n'.join(lines)


def updated_readme(readme, papers, tables):
    if readme.count(BEGIN) != 1 or readme.count(END) != 1 or readme.index(BEGIN) >= readme.index(END):
        raise ValueError('README must contain one ordered generation marker pair')
    before, rest = readme.split(BEGIN,1); _,after = rest.split(END,1)
    for name in ('mountain', 'relation', 'taxonomy'):
        before = re.sub(rf'(?:https://raw\.githubusercontent\.com/chonghanqin/Awesome-Agentic-Robots/main/)?assets/figures/{name}(?:-[a-f0-9]+)?\.webp(?:\?v=[a-f0-9]+)?', figure_src(name), before)
    return before+BEGIN+'\n\n'+render(papers,tables)+'\n'+END+after


def main():
    path=ROOT/'README.md'
    path.write_text(updated_readme(path.read_text(encoding='utf-8'),load_papers(),load_tables()),encoding='utf-8')
    print('Updated paper lists.')


if __name__ == '__main__': main()
