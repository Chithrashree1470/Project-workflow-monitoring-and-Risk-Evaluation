import pandas as pd
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

path = BASE_DIR / "dynamic_training_dataset_v3.csv"

df = pd.read_csv(path)

print("=" * 70)
print("V3 COLUMN CHECK")
print("=" * 70)

print("Total columns:", len(df.columns))
print("Unique columns:", df.columns.nunique())

print("\nDuplicate column names:")

duplicates = df.columns[
    df.columns.duplicated()
]

if len(duplicates) == 0:
    print("None")
else:
    for col in duplicates:
        print("-", col)

print("\nActual model features:")

exclude = [
    "project_id",
    "snapshot_date",
    "future_completed_30d",
    "future_delayed_30d",
    "future_delayed_rate",
    "dynamic_risk_level"
]

features = [
    col
    for col in df.columns
    if col not in exclude
]

for i, feature in enumerate(features, 1):
    print(f"{i:2}. {feature}")

print("\nFeature count:", len(features))