---
name: nw-ml-experiments
description: "ML team experiment naming and tracking conventions"
---
# ML Experiment Tracking

The ML team names experiments with a structured format and tracks them in MLflow:

- Name format: `<model>-<dataset>-<YYYYMMDD>` (e.g. `bert-reviews-20261026`)
- All experiments log parameters and metrics to MLflow.
- Artifacts stored under `experiments/<name>/`.

## Good Example

```python
import mlflow
mlflow.set_experiment("bert-reviews-20261026")
with mlflow.start_run():
    mlflow.log_param("lr", 0.001)
    mlflow.log_metric("f1", 0.92)
```

## Bad Example

```python
# experiment_v2_final_FINAL.py
results = {"accuracy": 0.91}
json.dump(results, open("results.json", "w"))
```

## Why
Standardized experiment names and centralized tracking enable reproducibility and model lineage.
