import pandas as pd
import numpy as np
from pathlib import Path
from contextlib import redirect_stdout

# ============================================================
# CONFIG
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

DATASET = BASE_DIR / "tawos_phase1_10history_dataset.csv"
OUTPUT_FILE = BASE_DIR / "tawos_dataset_analysis.txt"


# ============================================================
# LOAD DATASET
# ============================================================

df = pd.read_csv(DATASET, low_memory=False)


RISK_ORDER = [
    "Low",
    "Medium",
    "High",
    "Critical"
]

NUMERIC_FEATURES = [
    "story_points",
    "story_points_missing",
    "timespent",
    "task_age_days",
    "status_change_count",
    "priority_change_count",
    "assignee_change_count",
    "story_point_change_count",
    "estimate_change_count",
    "changes_last_7_days",
]

CATEGORICAL_FEATURES = [
    "issue_type",
    "priority",
    "status",
    "assignee",
    "sprint",
]


# ============================================================
# SAVE ALL OUTPUT TO TEXT FILE
# ============================================================

with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

    with redirect_stdout(f):

        # ====================================================
        # BASIC INFORMATION
        # ====================================================

        print("=" * 80)
        print("TAWOS DATASET ANALYSIS")
        print("=" * 80)

        print("\nDataset shape:")
        print("Rows   :", len(df))
        print("Columns:", len(df.columns))

        print("\nProjects :", df["project_id"].nunique())
        print("Issues   :", df["issue_id"].nunique())
        print("Snapshots:", len(df))


        # ====================================================
        # 1. RISK DISTRIBUTION
        # ====================================================

        print("\n" + "=" * 80)
        print("1. RISK DISTRIBUTION")
        print("=" * 80)

        risk_counts = df["task_risk_level"].value_counts()

        print(risk_counts)

        print("\nPercentages:")

        print(
            (
                df["task_risk_level"]
                .value_counts(normalize=True)
                * 100
            )
            .round(2)
        )


        # ====================================================
        # 2. NUMERIC FEATURES BY RISK
        # ====================================================

        print("\n" + "=" * 80)
        print("2. NUMERIC FEATURES BY RISK")
        print("=" * 80)

        numeric_summary = (
            df.groupby("task_risk_level")[NUMERIC_FEATURES]
            .agg(["mean", "median"])
            .reindex(RISK_ORDER)
        )

        print(
            numeric_summary.to_string()
        )


        # ====================================================
        # 3. NUMERIC FEATURE MEDIANS
        # ====================================================

        print("\n" + "=" * 80)
        print("3. NUMERIC FEATURE MEDIANS")
        print("=" * 80)

        median_table = (
            df.groupby("task_risk_level")[NUMERIC_FEATURES]
            .median()
            .reindex(RISK_ORDER)
            .T
        )

        print(
            median_table.to_string()
        )


        # ====================================================
        # 4. CATEGORICAL FEATURES VS RISK
        # ====================================================

        for feature in CATEGORICAL_FEATURES:

            print("\n" + "=" * 80)
            print(f"4. {feature.upper()} VS RISK")
            print("=" * 80)

            # -----------------------------------------------
            # Counts
            # -----------------------------------------------

            counts = pd.crosstab(
                df[feature],
                df["task_risk_level"]
            ).reindex(
                columns=RISK_ORDER,
                fill_value=0
            )

            print("\nCounts:")

            print(
                counts.to_string()
            )

            # -----------------------------------------------
            # Percentages
            # -----------------------------------------------

            percentages = (
                pd.crosstab(
                    df[feature],
                    df["task_risk_level"],
                    normalize="index"
                )
                .reindex(
                    columns=RISK_ORDER,
                    fill_value=0
                )
                * 100
            )

            print("\nRisk percentages within each value:")

            print(
                percentages
                .round(2)
                .to_string()
            )


        # ====================================================
        # 5. NUMERIC FEATURE CORRELATION
        # ====================================================

        print("\n" + "=" * 80)
        print("5. NUMERIC FEATURE CORRELATION")
        print("=" * 80)

        correlation = df[
            NUMERIC_FEATURES
        ].corr()

        print(
            correlation
            .round(3)
            .to_string()
        )


        # ====================================================
        # 6. FEATURES CORRELATED WITH TASK AGE
        # ====================================================

        print("\n" + "=" * 80)
        print("6. FEATURES CORRELATED WITH TASK AGE")
        print("=" * 80)

        age_correlation = (
            correlation["task_age_days"]
            .drop("task_age_days")
            .sort_values(
                key=abs,
                ascending=False
            )
        )

        print(
            age_correlation
            .round(3)
            .to_string()
        )


        # ====================================================
        # 7. FEATURES CORRELATED WITH CHANGE ACTIVITY
        # ====================================================

        print("\n" + "=" * 80)
        print("7. FEATURES CORRELATED WITH CHANGE ACTIVITY")
        print("=" * 80)

        change_features = [
            "status_change_count",
            "changes_last_7_days",
            "priority_change_count",
            "assignee_change_count",
            "story_point_change_count",
            "estimate_change_count",
        ]

        for feature in change_features:

            print(f"\n{feature}:")

            values = (
                correlation[feature]
                .drop(feature)
                .sort_values(
                    key=abs,
                    ascending=False
                )
            )

            print(
                values
                .round(3)
                .to_string()
            )


        # ====================================================
        # 8. TASK AGE DISTRIBUTION BY RISK
        # ====================================================

        print("\n" + "=" * 80)
        print("8. TASK AGE DISTRIBUTION BY RISK")
        print("=" * 80)

        age_stats = (
            df.groupby("task_risk_level")[
                "task_age_days"
            ]
            .describe()
            .reindex(RISK_ORDER)
        )

        print(
            age_stats
            .round(2)
            .to_string()
        )


        # ====================================================
        # 9. STATUS AND TASK AGE
        # ====================================================

        print("\n" + "=" * 80)
        print("9. STATUS AND TASK AGE")
        print("=" * 80)

        status_age = (
            df.groupby("status")[
                "task_age_days"
            ]
            .agg([
                "count",
                "mean",
                "median"
            ])
            .sort_values(
                "mean",
                ascending=False
            )
        )

        print(
            status_age
            .round(2)
            .to_string()
        )


        # ====================================================
        # 10. STATUS RISK SUMMARY
        # ====================================================

        print("\n" + "=" * 80)
        print("10. STATUS RISK SUMMARY")
        print("=" * 80)

        status_risk = (
            pd.crosstab(
                df["status"],
                df["task_risk_level"],
                normalize="index"
            )
            .reindex(
                columns=RISK_ORDER,
                fill_value=0
            )
            * 100
        )

        status_risk["High_or_Critical"] = (
            status_risk["High"]
            +
            status_risk["Critical"]
        )

        print(
            status_risk
            .sort_values(
                "High_or_Critical",
                ascending=False
            )
            .round(2)
            .to_string()
        )


        # ====================================================
        # 11. PRIORITY RISK SUMMARY
        # ====================================================

        print("\n" + "=" * 80)
        print("11. PRIORITY RISK SUMMARY")
        print("=" * 80)

        priority_risk = (
            pd.crosstab(
                df["priority"],
                df["task_risk_level"],
                normalize="index"
            )
            .reindex(
                columns=RISK_ORDER,
                fill_value=0
            )
            * 100
        )

        priority_risk["High_or_Critical"] = (
            priority_risk["High"]
            +
            priority_risk["Critical"]
        )

        print(
            priority_risk
            .sort_values(
                "High_or_Critical",
                ascending=False
            )
            .round(2)
            .to_string()
        )


        # ====================================================
        # 12. EARLY SNAPSHOT ANALYSIS
        # ====================================================

        print("\n" + "=" * 80)
        print("12. EARLY SNAPSHOT ANALYSIS")
        print("=" * 80)

        early = df[
            (df["task_age_days"] <= 7)
            &
            (df["status_change_count"] == 0)
            &
            (df["priority_change_count"] == 0)
            &
            (df["assignee_change_count"] == 0)
            &
            (df["story_point_change_count"] == 0)
            &
            (df["estimate_change_count"] == 0)
            &
            (df["changes_last_7_days"] == 0)
        ]

        print(
            "\nEarly snapshot rows:",
            len(early)
        )

        print("\nRisk distribution:")

        print(
            (
                early["task_risk_level"]
                .value_counts(normalize=True)
                * 100
            )
            .reindex(
                RISK_ORDER,
                fill_value=0
            )
            .round(2)
        )


        # ====================================================
        # 13. HIGH / CRITICAL TASK PROFILE
        # ====================================================

        print("\n" + "=" * 80)
        print("13. HIGH / CRITICAL TASK PROFILE")
        print("=" * 80)

        high_risk = df[
            df["task_risk_level"].isin(
                ["High", "Critical"]
            )
        ]

        print(
            "\nRows:",
            len(high_risk)
        )

        print("\nNumeric averages:")

        print(
            high_risk[
                NUMERIC_FEATURES
            ]
            .mean()
            .round(2)
            .sort_values(
                ascending=False
            )
            .to_string()
        )

        print("\nStatus distribution:")

        print(
            high_risk["status"]
            .value_counts()
            .to_string()
        )


        # ====================================================
        # 14. LOW / MEDIUM TASK PROFILE
        # ====================================================

        print("\n" + "=" * 80)
        print("14. LOW / MEDIUM TASK PROFILE")
        print("=" * 80)

        low_medium = df[
            df["task_risk_level"].isin(
                ["Low", "Medium"]
            )
        ]

        print(
            "\nRows:",
            len(low_medium)
        )

        print("\nNumeric averages:")

        print(
            low_medium[
                NUMERIC_FEATURES
            ]
            .mean()
            .round(2)
            .sort_values(
                ascending=False
            )
            .to_string()
        )


        # ====================================================
        # 15. KEY DATASET STATISTICS
        # ====================================================

        print("\n" + "=" * 80)
        print("15. KEY DATASET STATISTICS")
        print("=" * 80)

        print(
            "\nTask age by risk:\n",
            df.groupby(
                "task_risk_level"
            )["task_age_days"]
            .agg([
                "mean",
                "median"
            ])
            .reindex(RISK_ORDER)
            .round(2)
        )

        print(
            "\nStatus by risk:\n",
            status_risk.round(2)
        )

        print(
            "\nPriority by risk:\n",
            priority_risk.round(2)
        )

        print("\nAnalysis complete.")


# ============================================================
# TERMINAL MESSAGE
# ============================================================

print(
    f"Analysis saved to: {OUTPUT_FILE}"
)