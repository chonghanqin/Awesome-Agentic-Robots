#!/usr/bin/env python3
"""Check the public manuscript snapshot, safe markup and generated README."""
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
import re
import sys
from urllib.parse import urlsplit

import yaml

ROOT = Path(__file__).resolve().parents[1]
DOMAINS = {
    'Model': ['Training', 'Perception', 'Planning', 'Robot Control', 'Adaptation'],
    'Data': ['Collection', 'Annotation', 'Refinement'],
    'Environment': ['Reconstruction', 'Task Generation', 'Benchmarking'],
    'Harness': ['Orchestration', 'Memory', 'Monitoring and Recovery', 'Skills', 'Infrastructure', 'Layered Systems'],
}
TAXONOMY = {f'{domain.lower()}.{name.lower().replace(" ", "_")}': (domain, name)
            for domain, names in DOMAINS.items() for name in names}


class DisplayMarkup(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []

    def handle_starttag(self, tag, attrs):
        if tag not in ('strong', 'em', 'sup', 'sub') or attrs:
            raise ValueError('Unexpected display markup: ' + tag)
        self.stack.append(tag)

    def handle_endtag(self, tag):
        if not self.stack or self.stack.pop() != tag:
            raise ValueError('Unbalanced display markup')

    def handle_startendtag(self, tag, attrs):
        raise ValueError('Unexpected self-closing display markup')

    def handle_comment(self, data):
        raise ValueError('Unexpected display comment')

    def handle_decl(self, decl):
        raise ValueError('Unexpected display declaration')


def markup(value):
    if not isinstance(value, str) or '\\' in value:
        raise ValueError('Display fields must be converted HTML strings')
    parser = DisplayMarkup(); parser.feed(value); parser.close()
    if parser.stack: raise ValueError('Unclosed display markup')


def url(value, optional=False):
    if optional and value is None: return
    if not isinstance(value, str) or re.search(r'[\s<>"\\]', value):
        raise ValueError('Invalid public URL')
    parsed = urlsplit(value)
    if parsed.scheme not in ('http', 'https') or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Invalid public URL')


def load_records(name):
    data = yaml.safe_load((ROOT / 'data' / (name+'.yaml')).read_text(encoding='utf-8'))
    if not isinstance(data, list) or not data: raise ValueError('Expected nonempty '+name)
    return data


def load_papers(): return load_records('papers')
def load_tables(): return load_records('tables')


def load_publications(papers):
    data = yaml.safe_load((ROOT/'data/publications.yaml').read_text(encoding='utf-8'))
    if not isinstance(data, dict) or set(data) != {'checked_on', 'papers'}:
        raise ValueError('Invalid publication metadata')
    cutoff = date.fromisoformat(data['checked_on'])
    records = data['papers']
    if not isinstance(records, dict) or set(records) != {p['id'] for p in papers}:
        raise ValueError('Publication metadata must cover every work exactly once')
    for record in records.values():
        if set(record) != {'first_public', 'venue', 'venue_year', 'sources'}:
            raise ValueError('Invalid publication record')
        first = record['first_public']
        if first is not None:
            if not isinstance(first, str) or not re.fullmatch(r'\d{4}(?:-\d{2}(?:-\d{2})?)?', first):
                raise ValueError('Invalid first public date')
            padded = first + {4: '-01-01', 7: '-01', 10: ''}[len(first)]
            if date.fromisoformat(padded) > cutoff:
                raise ValueError('First public date is after the verification cutoff')
        if not isinstance(record['venue'], str) or not record['venue'].strip():
            raise ValueError('Missing venue')
        year = record['venue_year']
        if year is not None and (type(year) is not int or not 1900 <= year <= cutoff.year):
            raise ValueError('Invalid venue year')
        if first is None and year is None:
            raise ValueError('A record needs a verified date or venue year')
        if not isinstance(record['sources'], list) or not record['sources']:
            raise ValueError('Publication metadata needs source URLs')
        for source in record['sources']: url(source)
    return records


def load_additions(papers):
    additions = load_records('additional_papers')
    ids = {p['id'] for p in papers}
    for p in additions:
        if set(p) != {'id', 'title', 'categories', 'paper', 'code', 'venue', 'year'}:
            raise ValueError('Unexpected additional paper schema')
        if not isinstance(p['id'], str) or not re.fullmatch(r'[\w:.\-/]+', p['id']) or p['id'] in ids:
            raise ValueError('Duplicate or invalid additional paper identity')
        ids.add(p['id'])
        if not isinstance(p['title'], str) or not p['title'].strip():
            raise ValueError('Missing additional paper title')
        cats = p['categories']
        if not isinstance(cats, list) or not cats or len(cats) != len(set(cats)) or set(cats)-TAXONOMY.keys():
            raise ValueError('Unknown or duplicate additional paper placements')
        url(p['paper']); url(p['code'], optional=True)
        if not isinstance(p['venue'], str) or not p['venue'].strip() or type(p['year']) is not int:
            raise ValueError('Invalid additional paper venue or year')
    return additions


def validate(papers, tables):
    ids = {}; placements = set(); counts = Counter()
    for p in papers:
        if not isinstance(p, dict) or set(p) != {'id', 'title', 'categories'}:
            raise ValueError('Unexpected paper schema')
        if not re.fullmatch(r'[\w:.\-/]+', p['id']) or p['id'] in ids:
            raise ValueError('Duplicate or invalid manuscript identity')
        if not isinstance(p['title'], str) or not p['title'].strip(): raise ValueError('Missing title')
        cats = p['categories']
        if not isinstance(cats, list) or not cats or len(cats) != len(set(cats)) or set(cats)-TAXONOMY.keys():
            raise ValueError('Unknown or duplicate manuscript placements')
        ids[p['id']] = p
    if [t['key'] for t in tables] != list(TAXONOMY):
        raise ValueError('Tables must follow the full manuscript taxonomy and order')
    for t in tables:
        if set(t) != {'key', 'domain', 'category', 'headers', 'widths', 'caption', 'notes', 'rows'}:
            raise ValueError('Unexpected comparison-table schema')
        if TAXONOMY[t['key']] != (t['domain'], t['category']): raise ValueError('Category label mismatch')
        headers = t['headers']; widths = t['widths']
        if not 4 <= len(headers) <= 8 or headers[:2] != ['Work', 'Link'] or len(headers) != len(set(headers)):
            raise ValueError('Invalid comparison headers')
        for h in headers: markup(h)
        if len(widths) != len(headers) or any(type(w) not in (int,float) or w <= 0 for w in widths) or abs(sum(widths)-100) > .01:
            raise ValueError('Invalid comparison column widths')
        markup(t['caption'])
        for note in t['notes']: markup(note)
        if not isinstance(t['rows'], list) or not t['rows']: raise ValueError('Empty comparison table')
        seen = set()
        for row in t['rows']:
            if set(row) != {'bibkey','work','paper','code','code_partial','group','cells'}:
                raise ValueError('Unexpected comparison row schema')
            if row['bibkey'] not in ids: raise ValueError('Unknown comparison identity')
            markup(row['work'])
            if not row['work']: raise ValueError('Missing work label')
            if row['group'] is not None: markup(row['group'])
            if len(row['cells']) != len(headers)-2: raise ValueError('Incorrect comparison cell count')
            for cell in row['cells']: markup(cell)
            url(row['paper']); url(row['code'], optional=True)
            if type(row['code_partial']) is not bool or row['code_partial'] and not row['code']:
                raise ValueError('Invalid partial code release')
            # A work can appear in multiple annotation output groups.
            position = (row['bibkey'], row['group'])
            if position in seen: raise ValueError('Duplicate table group placement')
            seen.add(position); placements.add((row['bibkey'], t['key'])); counts[t['key']] += 1
    if placements != {(p['id'], c) for p in papers for c in p['categories']}:
        raise ValueError('Paper/table membership mismatch')
    return counts


def main():
    try:
        papers, tables = load_papers(), load_tables(); counts = validate(papers, tables)
        additions = load_additions(papers)
        publications = load_publications(papers + additions)
        from generate_readme import updated_readme, listing_rows
        readme = (ROOT/'README.md').read_text(encoding='utf-8')
        if updated_readme(readme, papers, tables) != readme: raise ValueError('README is stale')
        listed = sum(len(listing_rows(t, additions, publications)) for t in tables)
        print(f'PASS: {len(papers)+len(additions)} works, {len(tables)} paper lists, {listed} listed entries '
              f'({sum(counts.values())} source comparison rows)')
        for key,count in counts.items(): print(f'  {key}: {count} source rows')
    except (ValueError, OSError, KeyError, TypeError, yaml.YAMLError) as exc:
        print('FAIL: '+str(exc), file=sys.stderr); return 1
    return 0


if __name__ == '__main__': sys.exit(main())
