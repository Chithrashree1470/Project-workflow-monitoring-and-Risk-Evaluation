import pandas as pd
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATASET_PATH = (
    BASE_DIR / "data" / "tawos_phase1_history_dataset.csv"
)

OUTPUT_PATH = (
    BASE_DIR / "splits" / "phase1_30projects_split.json"
)

df = pd.read_csv(DATASET_PATH)

projects = sorted(
    df["project_id"].unique()
)

# Same deterministic split for both models
import numpy as np

rng = np.random.RandomState(42)
rng.shuffle(projects)

split_index = int(len(projects) * 0.8)

train_projects = sorted(
    [int(x) for x in projects[:split_index]]
)

test_projects = sorted(
    [int(x) for x in projects[split_index:]]
)

OUTPUT_PATH.parent.mkdir(
    exist_ok=True
)

with open(
    OUTPUT_PATH,
    "w"
) as f:

    json.dump(
        {
            "train_projects": train_projects,
            "test_projects": test_projects
        },
        f,
        indent=4
    )

print("=" * 70)
print("FIXED PROJECT SPLIT CREATED")
print("=" * 70)

print("\nTraining projects:")
print(train_projects)

print("\nTesting projects:")
print(test_projects)

print("\nSaved:")
print(OUTPUT_PATH)