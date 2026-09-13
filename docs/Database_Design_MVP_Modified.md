# Database Design (MVP)

# AI-Based Predictive Workflow Monitoring System

---

# Overview

This document describes the database design for the MVP of the AI-Based Predictive Workflow Monitoring System.

The database stores business data generated during project execution rather than storing machine-learning features directly. Workflow Monitoring derives current project-health indicators from project and task records. These derived indicators are supplied to the risk-prediction models.

The system uses a two-stage risk-assessment approach. The initial assessment uses project characteristics available when a project is created. As the project progresses, task updates are aggregated into current workflow indicators and used together with the original project characteristics to reassess project risk.

Pipeline:

```text
User Management
        ↓
Project & Task Management
        ↓
Application Database
        ↓
Workflow Monitoring
        ↓
KPI Calculation and Feature Engineering
        ↓
Initial / Dynamic Risk Prediction
        ↓
Dashboards
```

---

# Database Design Principles

- Store business entities, not permanently stored ML features.
- Keep the schema normalized.
- Store historical business events instead of overwriting important changes.
- Derive workflow KPIs from current database records.
- Use a consistent project-level feature representation for model training and live prediction.
- Keep the initial and dynamic risk-assessment processes connected through a common project-level representation.
- Ensure that every feature used by the deployed models can be obtained directly from the database or derived from stored records.
- Keep the schema easy to extend without requiring a complete redesign.

---

# Tables

## 1. Users

Stores all users in the system.

### Roles

- Manager
- Employee
- Client

### Columns

| Column | Type |
|---|---|
| user_id | UUID (PK) |
| full_name | VARCHAR(100) |
| email | VARCHAR(255) UNIQUE |
| password_hash | TEXT |
| role | ENUM |
| department | VARCHAR(100) |
| experience_level | ENUM |
| created_at | TIMESTAMP |

### Experience Level

Possible values:

- Intern
- Junior
- Mid
- Senior

Experience level is stored as a user attribute rather than duplicated in every task. When a task is assigned to an employee, the employee's experience can be obtained through `Tasks.assigned_to → Users.user_id`.

This information can support the proposed complexity-assessment component and can also be used for workload and team-composition analysis.

### Why this table?

Stores user information and controls access based on role.

---

## 2. Projects

Stores project-level information.

### Columns

| Column | Type |
|---|---|
| project_id | UUID (PK) |
| project_code | VARCHAR(8) UNIQUE |
| project_name | VARCHAR(150) |
| description | TEXT |
| manager_id | UUID (FK Users) |
| project_type | VARCHAR(50) |
| priority | ENUM |
| budget | DECIMAL(12,2) NULL |
| start_date | DATE |
| expected_end_date | DATE |
| actual_end_date | DATE NULL |
| status | ENUM |

### Why this table?

Stores the information available about a project independently of its individual tasks.

### Derived Project Information

`project_age_days` is not stored. It is calculated from:

```text
Current Date - start_date
```

Team size is also derived by counting active members in `ProjectMembers`.

---

## 3. ProjectMembers

Maps employees to projects.

### Columns

| Column | Type |
|---|---|
| project_member_id | UUID (PK) |
| project_id | UUID (FK Projects) |
| user_id | UUID (FK Users) |
| assigned_date | DATE |

### Why this table?

A project can contain multiple employees, and an employee can work on multiple projects. This resolves the many-to-many relationship.

The Workflow Monitoring module derives:

- Team size
- Team composition
- Employee experience distribution
- Employee workload across the project

from this table together with `Users` and `Tasks`.

---

## 4. ProjectClients

Maps clients to projects.

### Columns

| Column | Type |
|---|---|
| project_client_id | UUID (PK) |
| project_id | UUID (FK Projects) |
| client_id | UUID (FK Users) |

### Why this table?

Multiple clients can be associated with a project while keeping the database normalized.

---

## 5. Tasks

Stores all tasks belonging to a project.

### Columns

| Column | Type |
|---|---|
| task_id | UUID (PK) |
| project_id | UUID (FK Projects) |
| assigned_to | UUID (FK Users) |
| created_by | UUID (FK Users) |
| title | VARCHAR(150) |
| description | TEXT |
| task_type | VARCHAR(50) |
| priority | ENUM |
| weight | SMALLINT |
| estimated_hours | DECIMAL(6,2) |
| actual_hours | DECIMAL(6,2) NULL |
| start_date | DATE |
| deadline | DATE |
| completed_at | TIMESTAMP NULL |
| status | ENUM (TODO, IN_PROGRESS, DONE) |
| created_at | TIMESTAMP |

### Why this table?

Stores the current state of every task and provides the main source of execution data for Workflow Monitoring.

### Estimated Hours

Entered by the manager during task creation.

### Actual Hours

For the MVP, entered by the employee when marking a task as completed. Automatic time tracking is not required for the current implementation.

### Priority

Possible values:

- Low
- Medium
- High
- Critical

### Weight

Task weight determines how much a completed task contributes to overall project progress.

Example:

| Priority | Default Weight |
|---|---:|
| Low | 1 |
| Medium | 2 |
| High | 4 |
| Critical | 6 |

Managers may optionally override these values.

Project progress is calculated from completed task weights rather than manually entered task percentages.

### Employee Experience

Experience is not duplicated inside the Tasks table. It is obtained through:

```text
Tasks.assigned_to
        ↓
Users.user_id
        ↓
Users.experience_level
```

This allows the system to consider team composition and experience when calculating complexity without storing redundant information.

---

## 6. TaskHistory

Stores the history of important task events.

### Columns

| Column | Type |
|---|---|
| history_id | UUID (PK) |
| task_id | UUID (FK Tasks) |
| updated_by | UUID (FK Users) |
| change_type | ENUM |
| previous_status | ENUM NULL |
| new_status | ENUM NULL |
| remarks | TEXT NULL |
| updated_at | TIMESTAMP |

### Possible Change Types

- TASK_CREATED
- STATUS_CHANGE
- TASK_COMPLETED
- TASK_REOPENED
- ASSIGNMENT_CHANGE
- PRIORITY_CHANGE
- COMMENT

### Why this table?

Important business events are recorded instead of being lost when the current task state changes.

This supports:

- Activity history
- Timeline views
- Reopened-task detection
- Historical workflow analysis
- Future ML improvements

TaskHistory is not required for every current KPI. The initial dynamic-risk MVP can derive its main features from the current Tasks table, while TaskHistory provides additional temporal information as the system develops.

---

## 7. RiskPredictions

Stores historical risk predictions.

### Columns

| Column | Type |
|---|---|
| prediction_id | UUID (PK) |
| project_id | UUID (FK Projects) |
| prediction_time | TIMESTAMP |
| risk_level | ENUM |
| risk_score | DECIMAL(4,3) |
| confidence | DECIMAL(4,3) |
| model_version | VARCHAR(30) |

### Why this table?

Predictions should not overwrite previous predictions. Each prediction is stored as a historical snapshot.

Example:

```text
Project A

Initial assessment → Low Risk
Later assessment  → Medium Risk
Later assessment  → High Risk
```

This allows the system to show how project risk changes during execution.

---

# Workflow Monitoring and Feature Engineering

Workflow Monitoring acts as the bridge between the application database and the Machine Learning models.

It:

- Validates project and task data.
- Monitors task status and deadlines.
- Detects overdue tasks.
- Calculates project health KPIs.
- Aggregates task-level information into project-level indicators.
- Produces a consistent feature vector for model prediction.

The important design principle is that **task-level information is not passed directly to the project-risk model as a collection of individual records**. Instead, current task information is aggregated into project-level workflow indicators.

For example:

```text
Task 1 → DONE
Task 2 → DONE
Task 3 → IN_PROGRESS
Task 4 → OVERDUE
Task 5 → TODO
        ↓
Project-level workflow indicators
        ↓
Dynamic risk prediction
```

---

# Generated Project-Level Features

The following indicators can be derived from the application database.

| Feature | Source | Derivation |
|---|---|---|
| Total Tasks | Tasks | Count of tasks belonging to project |
| Completed Tasks | Tasks | Count where status = DONE |
| Pending Tasks | Tasks | Count where status = TODO |
| In-Progress Tasks | Tasks | Count where status = IN_PROGRESS |
| Project Progress (%) | Tasks | Completed task weight / total task weight × 100 |
| Overdue Tasks | Tasks | Tasks past deadline and not DONE |
| Delay Percentage | Tasks | Overdue tasks / total tasks × 100 |
| Average Delay Days | Tasks | Average overdue duration of currently delayed tasks |
| Employee Workload | Tasks + ProjectMembers | Active assigned work measured using active task count and/or estimated hours |
| Estimated Total Hours | Tasks | Sum of estimated_hours |
| Actual Total Hours | Tasks | Sum of recorded actual_hours |
| Effort Overrun (%) | Tasks | Difference between recorded actual and estimated effort |
| High-Priority Pending (%) | Tasks | Pending High/Critical tasks / pending tasks × 100 |
| Average Task Completion Time | Tasks | Average duration from start_date to completed_at |
| Project Age (Days) | Projects | Current date − start_date |
| Team Size | ProjectMembers | Count of active project members |
| Team Experience Distribution | ProjectMembers + Users | Distribution of assigned employees by experience_level |

### Effort Overrun

For projects with recorded actual effort:

```text
Effort Overrun (%) =
((Actual Total Hours - Estimated Total Hours)
 / Estimated Total Hours) × 100
```

For the MVP, actual effort is available when employees record actual hours on completed tasks. If insufficient actual-effort data is available, the feature should not be fabricated; it can be omitted until sufficient data exists.

---

# Initial Project Risk Assessment

The initial assessment is performed when sufficient project information is available at project initiation.

The model uses project-level characteristics such as:

- Project type
- Team size
- Budget
- Estimated timeline
- Complexity score
- Team experience
- Resource availability
- Stakeholder-related characteristics
- Technical characteristics
- Other project-level factors represented in the training dataset

The current prototype uses a **CatBoost multiclass classification model** to predict:

```text
Low Risk
Medium Risk
High Risk
```

The initial prediction represents the project's expected risk based primarily on its planned characteristics rather than its actual execution performance.

The existing project-level risk dataset is used for this initial model.

---

# Complexity Assessment

Project complexity is treated as an input to risk assessment.

The proposed complexity assessment considers characteristics such as:

```text
Project Characteristics
        +
Project Type
        +
Team Size and Team Composition
        +
Employee Roles
        +
Employee Experience
        +
Technical / Integration Characteristics
        +
Stakeholder / Requirement Characteristics
        ↓
Complexity Score
```

In the current MVP, the complexity score is supplied as an input value because the automated complexity calculation has not yet been fully implemented.

The database nevertheless stores the information required to support a future automated complexity module, including project type, team members, employee roles, and experience level. Additional stakeholder, requirement, and technical characteristics can be collected as project attributes when required.

---

# Dynamic Project Risk Assessment

The dynamic assessment does not produce an independent risk score for every task. Instead, task updates are used to determine the **current state of the project**, and this current state is used to reassess project-level risk.

The process is:

```text
Employee updates task
        ↓
Tasks table updated
        ↓
Workflow Monitoring
        ↓
Recalculate current project KPIs
        ↓
Combine with original project characteristics
        ↓
Dynamic CatBoost model
        ↓
Current Project Risk
```

The dynamic model therefore uses two categories of information:

### 1. Original Project Characteristics

These remain relatively stable during execution, such as:

- Project type
- Budget
- Planned timeline
- Team characteristics
- Complexity
- Other initial project attributes

### 2. Current Workflow Characteristics

These change as employees update tasks, such as:

- Project progress
- Completed tasks
- Pending tasks
- In-progress tasks
- Overdue tasks
- Delay percentage
- Average delay
- Employee workload
- Estimated effort
- Actual recorded effort
- High-priority pending work
- Average task completion time

The dynamic model is therefore a **project-level model whose inputs are updated using task-level execution data**.

---

# Relationship Between the Initial and Dynamic Models

The two models are related but serve different purposes.

```text
             PROJECT CREATION
                    ↓
          Initial Project Features
                    ↓
             Initial CatBoost
                    ↓
              Initial Risk
                    ↓
             PROJECT EXECUTION
                    ↓
            Employee Task Updates
                    ↓
             Workflow Monitoring
                    ↓
          Current Workflow KPIs
                    ↓
      Original Features + Current KPIs
                    ↓
             Dynamic CatBoost
                    ↓
             Current Project Risk
```

The initial model answers:

> What is the project's expected risk based on the information available at the beginning?

The dynamic model answers:

> What is the project's current risk after considering its observed execution performance?

This avoids treating completion percentage or overdue-task count as fixed project attributes. They are derived from tasks and change as the project progresses.

The dynamic model is trained separately from the initial model because it has an expanded feature space containing execution-related indicators. Both models can use common initial project characteristics, while the dynamic model additionally incorporates current workflow indicators.

---

# Dynamic Prediction Example

Consider a project that initially receives a Medium Risk prediction.

At the beginning:

```text
Initial Risk = Medium
```

After several task updates, Workflow Monitoring may calculate:

```text
Project Progress = 42%
Overdue Tasks = 8
Delay Percentage = 16%
Employee Workload = 0.82
High-Priority Pending = 40%
```

These current indicators are combined with the original project characteristics and supplied to the dynamic model.

The resulting prediction might become:

```text
Current Risk = High
```

A later improvement in project execution can result in a different prediction.

Thus, risk is treated as a changing project state rather than a single value calculated only once.

---

# Model Training and Live Prediction

The same feature definitions must be used during model training and live prediction.

For the dynamic model, training data should represent projects at observed points during execution, where task-level records are aggregated into project-level workflow features.

The task-level TAWOS dataset can be used to support development and validation of these workflow indicators. The deployed application does not need to use the TAWOS records directly. Instead, the application derives equivalent indicators from its own Tasks database.

```text
TAWOS Task-Level Data
        ↓
Develop / Validate Workflow Features
        ↓
Project-Level Dynamic Training Data
        ↓
Dynamic CatBoost Model
```

During application execution:

```text
Application Tasks
        ↓
Workflow Monitoring
        ↓
Same Feature Definitions
        ↓
Dynamic CatBoost Model
        ↓
Current Project Risk
```

---

# Feature Availability and Derivation

All features used by the application should either be stored directly or be deterministically derived from stored information.

| Required Information | Available From |
|---|---|
| Project type | Projects.project_type |
| Budget | Projects.budget |
| Planned deadline | Projects.expected_end_date |
| Project start | Projects.start_date |
| Team members | ProjectMembers |
| Team size | Derived from ProjectMembers |
| Employee role | Users.role |
| Employee experience | Users.experience_level |
| Task assignment | Tasks.assigned_to |
| Task priority | Tasks.priority |
| Task status | Tasks.status |
| Task deadline | Tasks.deadline |
| Estimated effort | Tasks.estimated_hours |
| Actual effort | Tasks.actual_hours |
| Task start | Tasks.start_date |
| Task completion | Tasks.completed_at |
| Task creation | Tasks.created_at |
| Task weight | Tasks.weight |
| Project progress | Derived from Tasks |
| Overdue tasks | Tasks + current date |
| Delay percentage | Derived from Tasks |
| Workload | Tasks + ProjectMembers |
| Effort overrun | Estimated/actual hours |
| Task completion time | start_date/completed_at |
| Historical task changes | TaskHistory |

No ML feature should require information that the application cannot obtain or derive.

---

# Data Flow

1. Manager creates a project.
2. Project characteristics are stored in `Projects`.
3. Employees are assigned through `ProjectMembers`.
4. Employee roles and experience are obtained from `Users`.
5. The system calculates or receives the project complexity information.
6. The initial CatBoost model predicts the project's initial risk.
7. Manager creates tasks.
8. Employees update task status and other task information.
9. Important task changes are recorded in `TaskHistory`.
10. Workflow Monitoring recalculates the current project KPIs.
11. Task-level information is aggregated into a project-level feature vector.
12. The dynamic CatBoost model uses the original project characteristics together with current workflow indicators.
13. The current risk prediction is stored in `RiskPredictions`.
14. Dashboards present the latest project state and risk history.

---

# System Views

The system provides separate views for employees, managers, and clients.

The purpose of these views is not only access control but also controlled transparency among stakeholders. Different stakeholders require different levels of project information, while managers require more detailed operational and risk information than clients or employees.

---

# ER Diagram Guide

Entities:

- Users
- Projects
- ProjectMembers
- ProjectClients
- Tasks
- TaskHistory
- RiskPredictions

Relationships:

```text
Users (1) -------- (M) ProjectMembers
Projects (1) ----- (M) ProjectMembers

Users (1) -------- (M) ProjectClients
Projects (1) ----- (M) ProjectClients

Projects (1) ----- (M) Tasks
Users (1) -------- (M) Tasks (Assigned To)
Users (1) -------- (M) Tasks (Created By)

Tasks (1) -------- (M) TaskHistory
Users (1) -------- (M) TaskHistory

Projects (1) ----- (M) RiskPredictions
```

Mark primary keys as **PK** and foreign keys as **FK**.

---

# MVP Scope

The current MVP focuses on:

- User and role management
- Project management
- Task management
- Task status and deadline monitoring
- Project-level workflow KPI calculation
- Initial project-level risk prediction
- Dynamic project-level risk reassessment
- Risk prediction history
- Role-based stakeholder views

The following can remain future enhancements:

- Automatic time tracking
- Advanced task-history-based features
- Experience-based automatic task assignment
- AI task recommendation
- GitHub/Jira integration
- Notifications
- Report generation
- Explainable AI
- Collaborative workspace features
