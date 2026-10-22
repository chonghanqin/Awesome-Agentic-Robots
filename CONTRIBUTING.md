# Contributing

We welcome paper and resource suggestions that fit the scope and taxonomy of **Towards Agentic Robots: Model, Data, Environment, and Harness**.

Please open a [paper suggestion](https://github.com/chonghanqin/Awesome-Agentic-Robots/issues/new?template=paper-suggestion.yml) with:

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

Each paper record contains a citation key (`id`), full title, and categories. The source comparison records store category placements and links. The README displays Publication, linked Paper Title, and Code, with one entry per work in each category. Annotation output groups are combined in that entry.

For new papers added directly to the collection, edit `data/additional_papers.yaml`. Each entry stores `id`, `title`, `categories`, `paper`, `code` (or `null`), `venue`, and `year`. These entries appear in the same category tables. This file is preserved when syncing the manuscript snapshot. When a paper enters the snapshot, remove its additional entry to avoid a duplicate identity.

Record verified publication metadata for every work in `data/publications.yaml`: `first_public` (ISO date, month, or year at the precision supported by the source; `null` if unresolved), `venue`, `venue_year` (or `null` if unverified), and supporting `sources`. Cross-check the manuscript bibliography against primary publication records. Use the earliest verified public release, not an arXiv revision, acceptance date, DOI registration date, or an inferred conference month. Use the conference edition year for venues, which can differ from the proceedings publication year. Preserve workshop/findings distinctions. Each category is sorted newest first; an entry without a verified release date is placed last within its venue year. Updating the manuscript snapshot does not overwrite these verified records.

To refresh the collection from Overleaf, run the sync command below. It uses the subsection tables selected by the current chapters and comparison switch, with full titles from `ref.bib`.

```sh
python3 scripts/sync_from_overleaf.py --overleaf /path/to/overleaf --write
python3 scripts/generate_readme.py
python3 scripts/validate.py
python3 scripts/sync_from_overleaf.py --overleaf /path/to/overleaf
```

The final command checks whether the snapshot matches the current manuscript. Keep fields, groups, row order, links, and notes aligned with the source tables. Technical cells support `<strong>`, `<em>`, `<sup>`, and `<sub>` markup.

The generator updates the marked paper-list region in the README. Edit the overview and citation outside that region directly. The validator checks data structure, table memberships, display markup, URLs, widths, and README freshness.
