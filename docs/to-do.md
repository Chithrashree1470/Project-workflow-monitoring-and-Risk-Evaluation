| Backend part                                   | Status                        |
| ---------------------------------------------- | ----------------------------- |
| Flask backend structure                        | ✅ Done                        |
| Supabase connection                            | ✅ Done                        |
| Project creation                               | ✅ Done                        |
| Initial project risk prediction                | ✅ Done                        |
| Project database storage                       | ✅ Done                        |
| Employee/client data                           | ✅ Done                        |
| Task creation API                              | ✅ Done                        |
| Task update API                                | ✅ Done                        |
| Task deletion API                              | ✅ Done                        |
| Task history / workflow tracking               | ✅ Done                        |
| Task-level CatBoost prediction                 | ✅ Done                        |
| Automatic risk prediction when task is created | ✅ Done                        |
| Current `task_risk_prediction`                 | ✅ Done                        |
| Dynamic project risk calculation               | ✅ Done                        |
| Project risk baseline comparison               | ✅ Done                        |
| Project risk trend                             | ✅ Done                        |
| `project_dynamic_risk`                         | ✅ Done                        |
| `project_dynamic_risk_history`                 | ✅ Done                        |
| Dashboard API/backend data                     | ✅ Mostly done                 |
| Project-details backend                        | ✅ Done                        |
| Task risk prediction on **task updates**       | 🟡 Needs completion           |
| Proper task-risk history tied to changes       | 🟡 Needs redesign             |
| `ABANDONED` task status                        | 🟡 Not implemented yet        |
| Project-specific unfinished-task calculation   | 🟡 Needs final verification   |
| Risk aggregation method                        | 🟡 Still needs final decision |
| Full backend integration testing               | 🟡 Remaining                  |
| Error handling/validation cleanup              | 🟡 Remaining                  |


Specifically, we should investigate these four things next:
Map your application statuses to the training dataset's status semantics, or retrain using your application's actual statuses.
Make sure task_age_days, timespent, and change-count features are calculated from your real task history rather than always starting at zero.
Check the model's feature importance to see what is actually driving predictions.
Test the trained model on deliberately constructed High/Critical scenarios and inspect the full probability distribution.



## retrain task level model at some point. 

The results reveal something important: priority is present in the training data, but its relationship with risk is inconsistent. I wouldn't change the model yet. There are a few data-quality issues worth investigating first.

## 1. Priority distribution

Number of historical snapshots for each priority.

Minor

Snapshots2,914

02,0004,0006,0008,000UnknownMediumMajor - P3LowMinorHighCritical

Three observations:

- Unknown accounts for 23.63% of all records. That's a substantial proportion.
- Critical accounts for only 3.98%.
- Priority values use different naming conventions: `Critical`, `Highest`, `Blocker`, `Critical - P2`, etc.

The model treats these as separate categorical values unless your preprocessing explicitly maps them.

## 2. Priority and risk relationship

Let's look at the latest snapshot percentages, which count each task only once.

| Priority | Low    | Medium | High   | Critical |
| -------- | ------ | ------ | ------ | -------- |
| Critical | 21.62% | 29.46% | 23.51% | 25.41%   |
| High     | 27.30% | 28.59% | 21.65% | 22.46%   |
| Medium   | 37.23% | 28.17% | 20.95% | 13.66%   |
| Low      | 25.48% | 23.81% | 23.06% | 27.65%   |
| Unknown  | 36.06% | 27.67% | 13.32% | 22.94%   |

Notice something unexpected:

- Critical priority has 25.41% Critical-risk tasks.
- High priority has 22.46%.
- Medium priority has 13.66%.
- Low priority has 27.65%.

Low priority actually has a higher Critical-risk proportion than High priority.

This explains why CatBoost doesn't necessarily produce a higher score whenever you increase priority.

## 3. The bigger problem: inconsistent priority values

Your dataset contains values such as:

| Value                    | Likely interpretation |
| ------------------------ | --------------------- |
| Blocker / Blocker - P1   | Highest urgency       |
| Critical / Critical - P2 | Very high urgency     |
| Major - P3               | Medium-high urgency   |
| Minor / Minor - P4       | Lower urgency         |
| Trivial / Trivial - P5   | Lowest urgency        |

These are not necessarily equivalent to your application's four values: `Low`, `Medium`, `High`, `Critical`.

We should investigate the original priority mapping before deciding whether to normalize them.

Also, `Unknown` represents 2,120 unique tasks. That means the model has a significant number of tasks where priority information is missing.

## 4. One important limitation in the current analysis

Your latest-snapshot analysis counts each task once, but it does not necessarily represent the exact training distribution.

Your training script uses historical snapshots. Therefore, the model learns from repeated observations of tasks as they evolve.

We should inspect both:

- Historical snapshot distribution.
- Latest snapshot distribution.

You have already obtained both, which is useful.

## 5. What I recommend doing next

Before changing the model, I would investigate priority normalization.

We should determine how the original TAWOS priorities map to the four categories used by your application.

For example, a possible mapping to investigate is:

| TAWOS priority                     | Application priority |
| ---------------------------------- | -------------------- |
| Blocker, Blocker - P1              | Critical             |
| Critical, Critical - P2, Highest   | Critical             |
| Major, Major - P3                  | Medium               |
| Medium                             | Medium               |
| Minor, Minor - P4                  | Low                  |
| Low, Lowest, Trivial, Trivial - P5 | Low                  |

This is only a proposed mapping, not something we should apply blindly. The source data's priority semantics need to be verified first.

My recommendation is to inspect the preprocessing code that creates `tawos_phase1_10history_dataset.csv`. We need to know whether priorities were normalized, left untouched, or converted inconsistently.

That will help us determine whether the problem originates in dataset preparation or in CatBoost's learned relationships.

## cautomate actual hours 

Your task-level CatBoost model currently takes 15 input features. We can inspect the training dataset to see the actual values and compare them with what your application sends during prediction.

## 1. Inputs taken by the task-level model

Based on your current `task_risk.py` and training script:

| Feature                    | Description                             |
| -------------------------- | --------------------------------------- |
| `issue_type`               | Task type, such as Task or Feature      |
| `priority`                 | Task priority                           |
| `status`                   | Current task status                     |
| `story_points`             | Estimated task complexity               |
| `story_points_missing`     | Whether story points are missing        |
| `timespent`                | Actual time spent                       |
| `assignee`                 | Assigned employee                       |
| `sprint`                   | Assigned sprint                         |
| `task_age_days`            | Task age in days                        |
| `status_change_count`      | Number of status changes                |
| `priority_change_count`    | Number of priority changes              |
| `assignee_change_count`    | Number of reassignment events           |
| `story_point_change_count` | Number of story point changes           |
| `estimate_change_count`    | Number of estimate changes              |
| `changes_last_7_days`      | Changes made during the last seven days |

## 2. Script to inspect unique values

Save this as `inspect_task_features.py` in your project root.

It will:

- Print all 15 features.
- Show unique values for categorical features.
- Show unique values and statistics for numeric features.
- Show missing-value counts.
- Save the complete report to `task_feature_analysis.txt`.

```
import pandas as pdfrom pathlib import PathBASE_DIR = Path(__file__).resolve().parentDATA_PATH = (    BASE_DIR    / "tawos_ml"    / "data"    / "tawos_phase1_10history_dataset.csv")OUTPUT_PATH = BASE_DIR / "task_feature_analysis.txt"FEATURES = [    "issue_type",    "priority",    "status",    "story_points",    "story_points_missing",    "timespent",    "assignee",    "sprint",    "task_age_days",    "status_change_count",    "priority_change_count",    "assignee_change_count",    "story_point_change_count",    "estimate_change_count",    "changes_last_7_days"]CATEGORICAL = [    "issue_type",    "priority",    "status",
```

Run:

```
python inspect_task_features.py
```

For numeric features with many distinct values, the report could be large. That's expected.

## 3. What values does your application use by default?

Based on the prediction code you previously shared:

| Feature                    | Default when missing                                                   |
| -------------------------- | ---------------------------------------------------------------------- |
| `issue_type`               | `"Unknown"` in feature preparation; task creation passes its task type |
| `priority`                 | `"Unknown"`                                                            |
| `status`                   | `"Unknown"`                                                            |
| `story_points`             | `0`                                                                    |
| `story_points_missing`     | `1` if story points are absent, otherwise `0`                          |
| `timespent`                | `0`                                                                    |
| `assignee`                 | `"Unknown"`                                                            |
| `sprint`                   | `"Unknown"`                                                            |
| `task_age_days`            | `0`                                                                    |
| `status_change_count`      | `0`                                                                    |
| `priority_change_count`    | `0`                                                                    |
| `assignee_change_count`    | `0`                                                                    |
| `story_point_change_count` | `0`                                                                    |
| `estimate_change_count`    | `0`                                                                    |
| `changes_last_7_days`      | `0`                                                                    |

Important distinction about story points:

If the user leaves story points empty:

```
story_points = 0story_points_missing = 1
```

If the user explicitly enters zero:

```
story_points = 0story_points_missing = 0
```

The missing indicator helps the model distinguish these situations.

These are the application-side defaults, not necessarily the most common values in your training dataset.

## 4. Should users fill in actual hours?

I would not expect users to enter actual hours when creating a task.

Your current mapping is:

```
"timespent": task.get("actual_hours") or 0
```

So if the user doesn't enter actual hours, the model receives `timespent = 0`.

That is reasonable when a task has just been created, but it becomes inaccurate if the task has been worked on and the user never updates the value.

## 5. How can we automate actual hours?

I recommend implementing a task timer and worklog system.

Suggested workflow

1

Employee starts working

Employee clicks `Start Timer` on the task.

2

Timer records start time

Backend stores the start timestamp and employee ID.

3

Employee stops working

Employee clicks `Stop Timer`.

4

Backend calculates elapsed time

The completed work session is saved.

5

Actual hours are updated

All completed work sessions are added together.

For example:

- Monday: 2 hours
- Tuesday: 1.5 hours
- Wednesday: 3 hours

`actual_hours = 6.5`

I would store individual sessions in a separate `task_worklogs` table rather than repeatedly overwriting the task's actual hours.

One important limitation: a timer measures recorded working sessions, not necessarily every minute someone actually works. Employees need to start and stop it consistently.

### My recommendation

For now:

1. Keep `actual_hours` defaulting to zero.
2. Don't make it a required task-creation field.
3. Keep the field editable for manual corrections.
4. Implement the timer/worklog feature later.
5. Automatically recalculate `actual_hours` from saved worklogs.

This will give your task-risk model a more meaningful `timespent` input without requiring employees to estimate their hours manually.



#  dynamically update model inputs

The important distinction is that the model takes 15 features, but the task creation form does not collect all 15 values directly. Some are collected from the user, some are derived from the database, and some are currently hardcoded defaults.

## 1. Comparing the task form with model inputs

Based on your task creation form and the prediction code you previously shared:

| Model feature              | Where does it come from? | Current behaviour                               |
| -------------------------- | ------------------------ | ----------------------------------------------- |
| `issue_type`               | Task Type field          | Defaults to `Task`                              |
| `priority`                 | Priority dropdown        | User selects it                                 |
| `status`                   | Status dropdown          | User selects it                                 |
| `story_points`             | Not in form              | Defaults to `0`                                 |
| `story_points_missing`     | Derived                  | `1` when story points are absent                |
| `timespent`                | Actual Hours field       | Defaults to `0`                                 |
| `assignee`                 | Assigned Employee ID     | User enters it                                  |
| `sprint`                   | Sprint field             | User enters it                                  |
| `task_age_days`            | Not in form              | Currently hardcoded to `0`                      |
| `status_change_count`      | Task history             | Currently hardcoded to `0` during task creation |
| `priority_change_count`    | Task history             | Currently hardcoded to `0` during task creation |
| `assignee_change_count`    | Task history             | Currently hardcoded to `0` during task creation |
| `story_point_change_count` | Task history             | Currently hardcoded to `0` during task creation |
| `estimate_change_count`    | Task history             | Currently hardcoded to `0` during task creation |
| `changes_last_7_days`      | Task history             | Currently hardcoded to `0` during task creation |

This means several model inputs are not yet dynamically populated.

## 2. How should we automate story points?

Story points represent the relative effort and complexity of a task. They shouldn't simply be calculated from priority.

I recommend a suggested story point estimation system.

For example, use the Fibonacci scale:

Suggested story point scale

# 1

Very simple

# 2

Simple

# 3

Small

# 5

Moderate

# 8

Complex

# 13

Very complex

### Proposed implementation

When a user enters:

- Task title
- Description
- Task type
- Priority

The system suggests story points.

For example:

| Task                           | Suggested points |
| ------------------------------ | ---------------- |
| Change button colour           | 1                |
| Add form validation            | 2                |
| Implement login authentication | 5                |
| Build payment integration      | 8                |

The user can accept or modify the suggestion.

How to generate the estimate?

We have three possible approaches:

1. Rule-based estimation: Use task type, keywords and complexity indicators. Simple, but limited.
2. AI-based estimation: Use an LLM to interpret the task title and description and suggest points.
3. Historical estimation: Learn from previously completed tasks and their actual effort or assigned story points.

I recommend starting with AI-based suggestions, with manual editing available. We should not automatically treat an AI estimate as ground truth.

Also, story points are not the same as hours. A task with 5 story points does not necessarily mean 5 hours.

## 3. Do default values update when the model runs again?

No, not automatically. Running CatBoost again does not update the source task data or calculate missing features.

Let's look at your current implementation.

| Feature                    | Does it update automatically with time? | What should happen?                      |
| -------------------------- | --------------------------------------- | ---------------------------------------- |
| `story_points`             | No                                      | User or estimation system supplies it    |
| `story_points_missing`     | No                                      | Recalculate whenever story points change |
| `timespent`                | No                                      | Update from worklogs                     |
| `task_age_days`            | No                                      | Calculate from task creation date        |
| `status_change_count`      | No                                      | Calculate from task history              |
| `priority_change_count`    | No                                      | Calculate from task history              |
| `assignee_change_count`    | No                                      | Calculate from task history              |
| `story_point_change_count` | No                                      | Calculate from task history              |
| `estimate_change_count`    | No                                      | Calculate from task history              |
| `changes_last_7_days`      | No                                      | Calculate from recent task history       |

For example, suppose a task was created on October 25.

On October 25:

```
task_age_days = 0
```

On October 30, it should be:

```
task_age_days = 5
```

But your current task creation helper sends `0`, and that value doesn't change merely because five days have passed.

Similarly, a task could have three priority changes in its history, but the current helper still sends `priority_change_count = 0` unless we explicitly calculate it.

### What about `Unknown`?

`Unknown` is a fallback used when a categorical feature is missing during prediction. It doesn't mean the database automatically fills the missing field.

If the actual priority is present, the model receives that priority instead.

## 4. What I recommend implementing

I would divide this into three stages.

Stage 1 — Task creation improvements

- Add a Story Points field.
- Add a Suggest Story Points action.
- Keep Actual Hours optional.
- Keep story points editable.

Stage 2 — Dynamic feature calculation

- Calculate task age from creation date.
- Calculate change counts from task history.
- Calculate changes in the last seven days.
- Recalculate `story_points_missing` whenever story points change.

Stage 3 — Actual work tracking

- Implement task timers.
- Store work sessions in a separate table.
- Calculate actual hours from recorded sessions.

One important technical point: We should ensure that the feature definitions and calculations match the training dataset. Otherwise, even correctly calculated values might have a different meaning from what CatBoost learned.

I would start with Stage 2's dynamic feature calculations alongside the story point field. These changes improve the quality of the existing model's inputs without requiring us to change or retrain the model.
