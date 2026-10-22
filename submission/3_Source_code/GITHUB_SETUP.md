# Publishing the source to GitHub

The Manuscript Guidelines ask for the source code to be loaded onto GitHub with
a link provided. The repository itself is the `PDS project` folder; these are
the exact commands to publish it.

## One-time setup

```bash
cd "C:\Users\durve\OneDrive\Desktop\PDS project"

git init
git add .
git commit -m "Digital Thread Analytics: lineage framework for the data science lifecycle"
```

`.gitignore` already excludes `data/`, `artifacts/`, `__pycache__/` and
`.venv/`, so generated files and the dataset are not committed. That is
deliberate: the pipeline regenerates them, and the guidelines ask for the
dataset in its own folder rather than in the repository.

## Create the remote

Either create an empty repository named `digital-thread-analytics` on
github.com and then:

```bash
git remote add origin https://github.com/<your-username>/digital-thread-analytics.git
git branch -M main
git push -u origin main
```

Or, if you have the GitHub CLI installed:

```bash
gh repo create digital-thread-analytics --public --source=. --remote=origin --push
```

## What to put in the manuscript

Add the resulting URL to the Data Availability Statement (Section XXIV) in
place of "available from the corresponding author on reasonable request", for
example:

> All source code generated during this study is available in the
> digital-thread-analytics repository, https://github.com/<your-username>/digital-thread-analytics

## Suggested repository description

> A digital thread for the data science lifecycle: an append-only, content-addressed
> lineage ledger linking raw data, validation, features, runs, models, deployments
> and drift into one bidirectionally traversable graph. Evaluated on AI4I 2020.
