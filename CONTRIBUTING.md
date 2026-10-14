# Contributing

We welcome paper and resource suggestions that fit the scope and taxonomy of **Towards Agentic Robots: Model, Data, Environment, and Harness**.

Please open a [paper suggestion](https://github.com/qinchonghanzuibang/Awesome-Agentic-Robots/issues/new?template=paper-suggestion.yml) with:

- Paper title and paper URL.
- Proposed category or categories from the README taxonomy.
- Official code URLs, if available.
- A 1–3 sentence explanation of how the work fits the collection.

Maintainers review suggestions for relevance and category placement.

## Local maintenance

Use Python 3.9 or newer. Install the single dependency in your preferred environment:

```sh
python3 -m pip install -r requirements.txt
```

Edit `data/papers.yaml` and `data/tables.yaml`, then run:

```sh
python3 scripts/generate_readme.py
python3 scripts/validate.py
```

Each paper record contains a citation key (`id`), full title, and categories. The comparison tables store headers, captions, groups, row order, links, and technical cells. Annotation methods can appear in multiple output groups.

To refresh the collection from Overleaf, run the sync command below. It uses the subsection tables selected by the current chapters and comparison switch, with full titles from `ref.bib`.

```sh
python3 scripts/sync_from_overleaf.py --overleaf /path/to/overleaf --write
python3 scripts/generate_readme.py
python3 scripts/validate.py
python3 scripts/sync_from_overleaf.py --overleaf /path/to/overleaf
```

The final command checks whether the snapshot matches the current manuscript. Keep fields, groups, row order, links, and notes aligned with the source tables. Technical cells support `<strong>`, `<em>`, `<sup>`, and `<sub>` markup.

The generator updates the marked comparison region in the README. Edit the overview and citation outside that region directly. The validator checks data structure, table memberships, display markup, URLs, widths, and README freshness.
