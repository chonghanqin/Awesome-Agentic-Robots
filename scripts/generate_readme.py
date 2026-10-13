#!/usr/bin/env python3
"""Render the current manuscript's comparison tables inside README markers."""
from html import escape
from urllib.parse import quote

from validate import DOMAINS, ROOT, load_papers, load_tables, validate

BEGIN = '<!-- BEGIN AUTO-GENERATED PAPER LIST -->'
END = '<!-- END AUTO-GENERATED PAPER LIST -->'


def link(label, url):
    target = escape(quote(url, safe=':/?#=&%+@~.-_'), quote=True)
    return f'<a href="{target}">{label}</a>'


def table_lines(table, papers):
    centered = {1} | {i+2 for i in range(len(table['headers'])-2)
                       if {row['cells'][i] for row in table['rows']} <= {'', '✓'}}
    lines = ['<table width="100%">', '<thead><tr>']
    lines += [f'<th width="{w:g}%" align="{"center" if i in centered else "left"}">{escape(h)}</th>'
              for i,(h,w) in enumerate(zip(table['headers'], table['widths']))]
    lines += ['</tr></thead>', '<tbody>']
    previous_group = None
    for row in table['rows']:
        if row['group'] != previous_group:
            if row['group']:
                lines.append(f'<tr><th colspan="{len(table["headers"])}" align="left">{row["group"]}</th></tr>')
            previous_group = row['group']
        title = escape(papers[row['bibkey']]['title'], quote=True)
        work = f'<span title="{title}">{row["work"]}</span>'
        links = link('Paper', row['paper']) + '<br>'
        links += link('Code', row['code']) if row['code'] else '—'
        if row['code_partial']: links += '<sup>†</sup>'
        cells = [work, links, *row['cells']]
        lines.append('<tr>'+''.join(('<td align="center">' if i in centered else '<td>')
                                       +c+'</td>' for i,c in enumerate(cells))+'</tr>')
    lines += ['</tbody>', '</table>', '', '<p>'+table['caption']+'</p>']
    if table['notes']: lines += ['<p>'+'<br>'.join(table['notes'])+'</p>']
    if any(row['code_partial'] for row in table['rows']): lines += ['<p><sup>†</sup> Partial code release.</p>']
    return lines


def render(papers, tables):
    validate(papers,tables); lookup = {p['id']:p for p in papers}; lines=[]
    for domain in DOMAINS:
        lines += [f'### {domain}', '']
        for table in tables:
            if table['domain'] == domain:
                lines += [f'#### {table["category"]}', '', *table_lines(table,lookup), '']
    return '\n'.join(lines)


def updated_readme(readme, papers, tables):
    if readme.count(BEGIN) != 1 or readme.count(END) != 1 or readme.index(BEGIN) >= readme.index(END):
        raise ValueError('README must contain one ordered generation marker pair')
    before, rest = readme.split(BEGIN,1); _,after = rest.split(END,1)
    return before+BEGIN+'\n\n'+render(papers,tables)+'\n'+END+after


def main():
    path=ROOT/'README.md'
    path.write_text(updated_readme(path.read_text(encoding='utf-8'),load_papers(),load_tables()),encoding='utf-8')
    print('Updated manuscript comparison tables.')


if __name__ == '__main__': main()
