import pandas as pd
import json
import random
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"

INPUT_FILE = DATA_DIR / "tawos_39projects_full_history_phase1.csv"
OUTPUT_FILE = DATA_DIR / "tawos_39project_split.json"

EXPECTED_PROJECT_COUNT = 39
TEST_PROJECT_COUNT = 8

df = pd.read_csv(INPUT_FILE)

projects = sorted(df["project_id"].dropna().unique().tolist())

print("Projects found:", len(projects))
print("Project IDs:", projects)

if len(projects) != EXPECTED_PROJECT_COUNT:
    raise ValueError(
        f"Expected {EXPECTED_PROJECT_COUNT} projects, "
        f"but found {len(projects)}"
    )

# Reproducible project-level split
random.seed(42)

shuffled = projects.copy()
random.shuffle(shuffled)

test_projects = sorted(shuffled[:TEST_PROJECT_COUNT])
train_projects = sorted(shuffled[TEST_PROJECT_COUNT:])

if set(train_projects) & set(test_projects):
    raise ValueError("Train/test project overlap detected!")

if len(train_projects) + len(test_projects) != 39:
    raise ValueError("Incorrect train/test project count!")

split = {
    "train_projects": train_projects,
    "test_projects": test_projects,
    "random_seed": 42
}

with open(OUTPUT_FILE, "w") as f:
    json.dump(split, f, indent=4)

print("\nTRAIN PROJECTS:")
print(train_projects)

print("\nTEST PROJECTS:")
print(test_projects)

print("\nTrain project count:", len(train_projects))
print("Test project count:", len(test_projects))

print(f"\nSaved split to: {OUTPUT_FILE}")