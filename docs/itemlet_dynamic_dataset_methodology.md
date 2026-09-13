# Itemlet Dataset Processing for Dynamic Project Risk Prediction

## 1. Purpose

The Itemlet dataset is used as the historical task-execution dataset for the **dynamic project risk prediction** component of the AI-Based Workflow Monitoring System.

The objective is not to use Itemlet's precomputed risk scores directly. Instead, task execution information is transformed into **time-based project snapshots**, and a future execution outcome is derived to serve as the target for a Dynamic CatBoost model.

---

## 2. Source Dataset

The downloaded Itemlet dataset contains task/issue-level records from software projects.

The relevant fields selected for the dynamic-risk pipeline include:

### Project and task identification

| Column | Why it is relevant |
|---|---|
| `project_id` | Groups tasks into projects and allows project-level snapshots to be constructed. |
| `project_key` | Identifies the project using its project key. |
| `issue_key` | Identifies the task/issue within a project. Used with `project_id` to form a task identity. |

### Task characteristics

| Column | Why it is relevant |
|---|---|
| `issuetype_name` | Provides the type of work, such as Bug or Story. Task-type composition can influence project execution behavior. |
| `priority_name` | Represents task priority. A high concentration of Critical/High-priority tasks can indicate greater execution pressure. |
| `status_name` | Represents the current task status. |
| `status_statusCategory_name` | Provides a normalized status category and helps distinguish completed work from work that remains active. |

### Temporal/execution fields

| Column | Why it is relevant |
|---|---|
| `created` | Establishes when a task entered the project. It is required to reconstruct the project state at a particular point in time. |
| `updated` | Indicates recent task activity and helps establish the project's activity period. |
| `resolutiondate` | Indicates when a task was resolved. It is used to determine completion and calculate task cycle time. |

### Workflow-history indicators

| Column | Why it is relevant |
|---|---|
| `Transition Count` | Measures workflow/status transitions and therefore task activity. |
| `Reassignment Count` | Measures how often task responsibility changed. |
| `Reopen Count` | Captures tasks that had to be reopened, representing execution instability. |
| `Updated By Count` | Measures the number of distinct users contributing updates. |
| `Assignee Count` | Captures assignment-related activity. |

### Optional historical fields

`story_points`, work-log fields, and dependency/link fields were considered during dataset preparation. They were not made required dynamic-model inputs because the proposed application does not currently provide reliable equivalents for them.

In particular:

- Story points have substantial missingness in Itemlet.
- The application does not currently implement work logging.
- The application does not currently store task dependency relationships.

Therefore, these fields were excluded from the core MVP feature set rather than requiring users to provide information that the application cannot reproduce.

---

## 3. Task Identity

An important property of the Itemlet data was discovered during inspection.

`issue_id` is not globally unique across the dataset. The same numeric issue ID can occur in different projects.

Therefore, task identity is constructed as:

```text
task_id = project_id + "_" + issue_key
```

This prevents unrelated issues from different projects from being treated as the same task.

After applying this identity to the cleaned Itemlet dataset, the task records used for the dynamic dataset were unique.

---

## 4. Data Cleaning and Preparation

The preparation pipeline performs the following operations:

1. Load `itemlet_relevant.csv`.
2. Convert `created`, `updated`, and `resolutiondate` to UTC-aware datetime values.
3. Convert execution-count fields to numeric values.
4. Remove records without a project ID or task/issue key.
5. Remove exact duplicate rows.
6. Construct a project-specific task identifier using `project_id + issue_key`.
7. Determine whether a task has been completed using the presence of a resolution date.
8. Calculate task cycle time.

### Cycle Time

For completed tasks:

```text
Cycle Time =
resolutiondate - created
```

expressed in hours.

This represents the observed duration between task creation and resolution.

---

## 5. Identifying Delayed Tasks

The dynamic model needs a future execution outcome.

Instead of using Itemlet's precomputed `effort_risk_score` or assigning a manually invented risk label, the pipeline derives an outcome from actual task execution.

For each project, the cycle-time distribution of completed tasks is calculated.

The **75th percentile of cycle time within each project** is used as the project-specific delay threshold.

A completed task is marked as unusually delayed when:

```text
task cycle time > project's 75th-percentile cycle time
```

This is a relative measure: a task is considered delayed compared with the normal execution duration observed in its own project.

This approach is consistent with the concept represented by Itemlet's `is_long_running` field, which uses a project-level 75th-percentile cycle-time criterion.

---

# 6. Creating Project Snapshots

The original Itemlet data is task-level data.

A dynamic risk model, however, needs to learn from the **state of a project at different points in time**.

Therefore, the task records are transformed into periodic project snapshots.

### Snapshot frequency

Snapshots are generated at **weekly intervals (7 days)** throughout each project's observed activity period.

For example:

```text
Project A

Week 1 snapshot
Week 2 snapshot
Week 3 snapshot
Week 4 snapshot
...
```

Each snapshot represents the information that would have been available about the project at that point in time.

---

## 7. Current-State Features

For each snapshot, task information available up to that snapshot is aggregated into project-level features.

Examples include:

```text
total_tasks
completed_tasks
pending_tasks
completion_percentage
project_age_days
transition_count
reassignment_count
reopen_count
updated_by_count
assignee_count
critical_task_count
high_priority_task_count
bug_count
story_count
```

### Example

Suppose a project has the following state at a particular snapshot:

```text
Total tasks       = 100
Completed tasks   = 60
Pending tasks     = 40
Completion        = 60%
Reopens           = 8
Reassignments     = 15
Transitions       = 180
Critical tasks    = 10
Bug tasks         = 30
```

That complete state becomes **one training observation**.

A later snapshot produces another observation:

```text
Total tasks       = 120
Completed tasks   = 80
Pending tasks     = 40
Completion        = 66.7%
Reopens           = 10
Reassignments     = 18
Transitions       = 230
...
```

Thus, one historical project can contribute multiple training observations.

This is what makes the dataset suitable for dynamic prediction.

---

# 8. Future Outcome and Target Construction

The model must predict what is likely to happen **after the current project state**.

For each snapshot at time `T`, the pipeline examines task outcomes occurring during the following **30-day forecast window**:

```text
Snapshot T
    |
    |---- next 30 days ----|
    T                     T+30 days
```

The 30-day period is therefore a **forecast horizon**, not the definition of what constitutes risk.

During this future window we count:

```text
Future completed tasks
Future delayed tasks
```

where a delayed task is one whose eventual cycle time exceeds its project's 75th-percentile threshold.

The continuous future outcome is:

```text
Future Delayed Rate =
Future delayed tasks
--------------------
Future completed tasks
```

For example:

```text
Future completed tasks = 20
Future delayed tasks   = 5

Future delayed rate = 5 / 20 = 0.25
```

Therefore, the snapshot has a future delayed-task rate of **25%**.

---

# 9. Synthesizing the Dynamic Risk Labels

The Itemlet dataset does not provide the exact project-level future risk label required by this application.

Therefore, the dynamic risk class is derived from the observed future execution outcome.

The distribution of `future_delayed_rate` across valid snapshots is divided using the **33rd and 66th percentiles**.

The resulting labels are:

```text
Lower third     → Low
Middle third    → Medium
Upper third     → High
```

This is a **data-driven labeling strategy**.

It should not be interpreted as a universal project-management rule such as "25% delayed always means High Risk." Instead, it ranks snapshots according to the future execution behavior observed in the Itemlet sample.

The resulting dataset currently contains:

```text
Projects : 105
Snapshots: 28,843

Low      : 9,520
Medium   : 9,516
High     : 9,807
```

The classes are therefore reasonably balanced for multiclass model training.

---

# 10. Final Dynamic Dataset Structure

The resulting `dynamic_training_dataset.csv` contains project snapshots rather than individual raw Itemlet tasks.

Core predictive features include:

```text
project_id
snapshot_date
project_age_days

total_tasks
completed_tasks
pending_tasks
completion_percentage

transition_count
reassignment_count
reopen_count
updated_by_count
assignee_count

critical_task_count
high_priority_task_count
bug_count
story_count
```

Future-outcome fields are retained in the dataset for analysis and validation:

```text
future_completed_30d
future_delayed_30d
future_delayed_rate
dynamic_risk_level
```

However, the future-outcome fields must **NOT** be supplied to the Dynamic CatBoost model as input features.

They are used to construct/evaluate the target.

Otherwise, the model would suffer from **data leakage**, because it would be given information about the future that it is supposed to predict.

---

# 11. How This Maps to the Application

The historical Itemlet dataset is used for model training.

The deployed application does not need Itemlet itself.

Instead, the application collects task information that it can actually support:

### User/task information

```text
Task type
Priority
Status
Assignee
```

The system automatically records:

```text
Created timestamp
Updated timestamp
Resolution timestamp
Status transitions
Reassignments
Reopens
```

The application then aggregates these task records into the same type of current project state used during model training:

```text
Task records
     ↓
Project snapshot/state
     ↓
Dynamic features
     ↓
Dynamic CatBoost
     ↓
Current project risk
```

Therefore, the dynamic model can eventually operate on the application's own live task data rather than requiring users to manually enter derived statistics.

---

# 12. Relationship with Initial Project Risk Prediction

The Itemlet-derived dynamic dataset is **not intended to replace the existing initial project-risk dataset**.

The two models serve different purposes.

### Initial prediction

Uses project information available before execution:

```text
Project characteristics
        ↓
Initial CatBoost
        ↓
Initial project risk
```

### Dynamic prediction

Uses actual execution/workflow information after the project begins:

```text
Task updates
      ↓
Current project state
      ↓
Dynamic CatBoost
      ↓
Current project risk
```

The two predictions can therefore be connected:

```text
                 PROJECT CREATION
                       |
                       v
              Initial Risk Model
                       |
                       v
                 Initial Risk
                       |
                  Project starts
                       |
                       v
                 Task activity
                       |
                       v
              Dynamic Risk Model
                       |
                       v
                 Current Risk
```

The dynamic model is intended to update the project's risk assessment as real execution data accumulates.

---

# 13. Why Itemlet Is Used for Dynamic Risk

The initial project-risk dataset contains many project-level characteristics but does not provide the detailed temporal task-execution history required to study changing workflow conditions.

Itemlet supplies task-level execution information such as:

- task creation and resolution times,
- workflow transitions,
- reassignments,
- reopens,
- task types,
- priorities,
- and project membership.

These allow the construction of historical project snapshots and future execution outcomes.

Thus, Itemlet complements rather than replaces the initial project-level dataset.

---

# 14. Current Status

The dynamic dataset construction stage is complete.

Current output:

```text
dynamic_training_dataset.csv
```

with:

```text
105 projects
28,843 project snapshots
20 columns
3 balanced dynamic-risk classes
```

The next stage is to train and evaluate a **Dynamic CatBoost multiclass classifier** using only information available at each snapshot and using `dynamic_risk_level` as the target.

