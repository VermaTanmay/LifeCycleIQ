# LifeCycleIQ – Employee Lifecycle & Workflow Orchestration

A deterministic synthetic-data and workflow foundation for the YottaFlex.ai Associate AI Forward Deployed Engineer challenge.

## Current implementation

- Normalized SQLite schema for the 12 required core entities plus relationship/history tables.
- Deterministic synthetic data generator (seed `20261022`).
- Configurable scale; default target: 1,000 employees, 8,000 tasks, 1,500 access grants and 1,200 assets.
- Separate ground-truth labels for deliberately injected anomalies.
- Validation for primary keys, foreign keys, date/lifecycle rules, task dependencies, access and asset reconciliation.
- CSV exports, JSON manifest, SQLite database and reproducibility checks.

## Requirements

- Python 3.10+
- No third-party packages are required for the data-generation stage.

## Quick start (Windows PowerShell)

```powershell
cd lifecycleiq
python -m venv .venv
.venv\Scripts\Activate.ps1
python backend\generator\generate_data.py --output data\generated --seed 20261022
python backend\generator\validate_data.py --db data\generated\lifecycleiq.db --report data\generated\validation_summary.json
python backend\generator\reproducibility_check.py
```

## Quick start (macOS/Linux)

```bash
cd lifecycleiq
python3 -m venv .venv
source .venv/bin/activate
python backend/generator/generate_data.py --output data/generated --seed 20261022
python backend/generator/validate_data.py --db data/generated/lifecycleiq.db --report data/generated/validation_summary.json
python backend/generator/reproducibility_check.py
```

## Scale configuration

```bash
python backend/generator/generate_data.py \
  --output data/generated \
  --seed 20261022 \
  --employees 1000 \
  --tasks 8000 \
  --grants 1500 \
  --assets 1200
```

For a quick smoke test, use `--employees 30 --tasks 240 --grants 45 --assets 36`.

## Important design decisions

1. Master data is created before dependent records.
2. IDs are deterministic and immutable.
3. Baseline records are generated before labelled anomalies are injected.
4. `ground_truth/ground_truth.csv` is kept separate from operational input tables.
5. State changes are represented as audit events; event history is not overwritten.
6. The validation report distinguishes expected labelled anomalies from unexpected integrity failures.

## Project layout

```text
backend/
  app/                  # API and workflow services (next implementation stage)
  generator/            # synthetic data generation and validation
  tests/                # automated tests
data/
  generated/            # generated SQLite, CSV and manifests
  ground_truth/         # known anomaly labels; never use as model input
docs/
  data_dictionary.md
  architecture.md
```

## Lawful provenance

All generated records are synthetic. No personal or confidential employee data is collected or used.
