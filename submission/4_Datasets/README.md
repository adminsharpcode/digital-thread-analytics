# Datasets and results

## `ai4i2020.csv`

**This is a specification replica, not the original UCI file.** The machine that
ran the experiments could not reach `archive.ics.uci.edu`, so the pipeline
generated this file from the dataset's published description: the documented
marginal distributions of the six process variables, the five independent
failure mechanisms (TWF, HDF, PWF, OSF, RNF) and the documented overall failure
rate of 3.39 %.

The generator is `pipeline/common.py::generate_ai4i` and is reproducible from
the seed in `config/config.yaml`.

Original dataset: S. Matzka, "AI4I 2020 Predictive Maintenance Dataset," UCI
Machine Learning Repository, 2020, doi: 10.24432/C5HS5C.

## Results files

| File | Contents |
|---|---|
| `framework_evaluation.json` | Every number reported in Section XVI: reproducibility, completeness, trace times, overhead decomposition, ledger census |
| `training_metrics.json` | The five metrics for both candidate models |
| `drift_report.json` | Population stability index per feature, threshold, and the simulation parameters |
| `thread_ledger_graph.html` | The full lineage graph rendered as a self-contained page. Open it in any browser; it needs nothing installed. |
