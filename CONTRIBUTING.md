# Contributing

We welcome paper and resource suggestions that fit the scope and taxonomy of **Towards Agentic Robots: Model, Data, Environment, and Harness**.

Please open a [paper suggestion](https://github.com/qinchonghanzuibang/Awesome-Agentic-Robots/issues/new?template=paper-suggestion.yml) with:

- Paper title and paper URL.
- Proposed category or categories from the README taxonomy.
- Official code URLs, if available.
- A 1–3 sentence explanation of how the work fits the collection.

Inclusion depends on relevance to the companion survey and support for the proposed placement. Suggestions are reviewed by the maintainers; submission does not guarantee inclusion.

## Local maintenance

Use Python 3.9 or newer. Install the single dependency in your preferred environment:

```sh
python3 -m pip install -r requirements.txt
```

Edit `data/papers.yaml`, then run:

```sh
python3 scripts/generate_readme.py
python3 scripts/validate.py
```

Each paper has a manuscript citation key (`id`), full `title`, and visible `categories`. Each comparison table in `data/tables.yaml` has its own headers, column widths, caption, notes, groups, row order, paper/code links, and technical cells. Multiple annotation groups may include the same work. Do not collapse those rows or infer that an unmarked persistence cell means explicitly absent.

For a manuscript refresh, use the active subsection tables included by the current Overleaf chapters. The comparison switch selects the current Model, Environment, and Harness tables; Data includes its comparison tables directly. Earlier literature tables and comparison JSON may be historical or differ from hand-edited active tables. `ref.bib` supplies full titles; citation keys preserve manuscript identity. The sync command reads the Overleaf repository without writing it and fails on unknown display commands:

```sh
python3 scripts/sync_from_overleaf.py --overleaf /path/to/overleaf --write
python3 scripts/generate_readme.py
python3 scripts/validate.py
python3 scripts/sync_from_overleaf.py --overleaf /path/to/overleaf
```

The final command checks exact snapshot freshness without writing. Preserve subsection-specific fields, grouping, row order, qualifiers, source links and notes. Add or change technical cells only when supported by the manuscript/source review. Public comparison cells support only `<strong>`, `<em>`, `<sup>` and `<sub>` markup without attributes; all URLs are validated separately. Evidence logs, private reviews, source PDFs, backups, and local paths stay outside the public dataset.

The README generator reads the two YAML files and changes only the marked comparison region. Edit the overview and citation outside that region directly. Validation checks structure, memberships, safe display markup, links, widths and README freshness; it does not independently establish scientific truth or verify remote link availability.
