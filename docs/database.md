# Database Design (MVP)

# AI-Based Predictive Workflow Monitoring System

---

# Overview

This document describes the database design for the MVP.

The purpose of the database is **not** to store Machine Learning features directly. Instead, it stores business data generated during project execution. The Workflow Monitoring module derives project health metrics (KPIs) from this data, which are then used bProject management Risk Raw

Code

Download
About Dataset
Welcome to the Project management Risk Dataset, a robust designed collection of 50 simulated project management related data points suited for practicing Exploratory Data Analysis and machine learning.

With help of AI I tried to provide relevant features and interdependencies between the datapoints. The Dataset consists of project essential categories such as:

Project Demographics: Project_Type, Project_Budget_USD, Estimated_Timeline_Months, Team_Size, Complexity_Score.
Operational Metrics: Change_Request_Frequency, Budget_Utilization_Rate, Resource_Availability, Current_Phase_Duration_Months.
Human Factors: Team_Experience_Level, Project_Manager_Experience, Stakeholder_Engagement_Level, Team_Turnover_Rate.
Organizational Context: Org_Process_Maturity, Regulatory_Compliance_Level, Funding_Source, Risk_Management_Maturity.
Technical Aspects: Technology_Familiarity, Technical_Debt_Level, Integration_Complexity, Tech_Environment_Stability.
External Influences: Market_Volatility, Industry_Volatility, External_Dependencies_Count, Client_Experience_Level.
This makes it a perfect fit for:

Practice Exploratory Data Analysis (EDA).
Building predictive models to forecast project success or potential failure.
Developing classification algorithms for early risk identification and mitigation strategies.
Conducting in-depth feature engineering to uncover hidden patterns and correlations.
Simulating scenarios to understand the impact of various project decisions on overall ry the Machine Learning model for risk prediction.

Pipeline:

```
Phase 1 → User Management
        ↓
Phase 2 → Project & Task Management
        ↓
Application Database
        ↓
Phase 3 → Workflow Monitoring
        ↓
Phase 4 → Machine Learning Risk Prediction
        ↓
Phase 5 → Dashboards
```

---

# Database Design Principles

- Store business entities, not ML features.
- Keep the schema normalized.
- Store historical business events instead of overwriting them.
- Workflow Monitoring computes KPIs from database records.
- Machine Learning consumes KPIs, not raw database tables.
- The schema should be easy to extend without redesigning the database.

---

# Tables

## 1. Users

Stores all users in the system.

### Roles

- Manager
- Employee
- Client

### Columns

| Column        | Type                |
| ------------- | ------------------- |
| user_id       | UUID (PK)           |
| full_name     | VARCHAR(100)        |
| email         | VARCHAR(255) UNIQUE |
| password_hash | TEXT                |
| role          | ENUM                |
| department    | VARCHAR(100)        |
| created_at    | TIMESTAMP           |

### Why this table?

Stores user information and controls access based on role.

### Future Scope

Add an **Experience Level** field.

Possible values:

- Intern
- Junior
- Mid
- Senior

This can later be used by Machine Learning for better effort estimation and intelligent task assignment.

---

## 2. Projects

Stores software project information.

### Columns

| Column            | Type               |
| ----------------- | ------------------ |
| project_id        | UUID (PK)          |
| project_code      | VARCHAR(8) UNIQUE  |
| project_name      | VARCHAR(150)       |
| description       | TEXT               |
| manager_id        | UUID (FK Users)    |
| project_type      | VARCHAR(50)        |
| priority          | ENUM               |
| budget            | DECIMAL(12,2) NULL |
| start_date        | DATE               |
| expected_end_date | DATE               |
| actual_end_date   | DATE NULL          |
| status            | ENUM               |

### Why this table?

Stores project-level information.

Project Code is a short human-readable identifier (e.g., **PRJ-A8F3KQ**) that is easier to search and communicate than a UUID.

**Note**

`project_age_days` is **not stored** in the database.

It is calculated by the Workflow Monitoring module using:

```
Current Date - start_date
```

This derived feature is passed to the Machine Learning model.

---

## 3. ProjectMembers

Maps employees to projects.

### Columns

| Column            | Type               |
| ----------------- | ------------------ |
| project_member_id | UUID (PK)          |
| project_id        | UUID (FK Projects) |
| user_id           | UUID (FK Users)    |
| assigned_date     | DATE               |

### Why this table?

A project contains many employees, and an employee may work on multiple projects.

This resolves the many-to-many relationship.

**Note**

The Workflow Monitoring module calculates **team_size** by counting the number of active members assigned to a project.

This value is derived and is not stored separately.

---

## 4. ProjectClients

Maps clients to projects.

### Columns

| Column            | Type               |
| ----------------- | ------------------ |
| project_client_id | UUID (PK)          |
| project_id        | UUID (FK Projects) |
| client_id         | UUID (FK Users)    |

### Why this table?

Multiple clients can monitor the same project.

This also keeps the schema normalized.

---

## 5. Tasks

Stores all tasks belonging to a project.

### Columns

| Column          | Type                           |
| --------------- | ------------------------------ |
| task_id         | UUID (PK)                      |
| project_id      | UUID (FK Projects)             |
| assigned_to     | UUID (FK Users)                |
| created_by      | UUID (FK Users)                |
| title           | VARCHAR(150)                   |
| description     | TEXT                           |
| task_type       | VARCHAR(50)                    |
| priority        | ENUM                           |
| weight          | SMALLINT                       |
| estimated_hours | DECIMAL(6,2)                   |
| actual_hours    | DECIMAL(6,2) NULL              |
| start_date      | DATE                           |
| deadline        | DATE                           |
| completed_at    | TIMESTAMP NULL                 |
| status          | ENUM (TODO, IN_PROGRESS, DONE) |
| created_at      | TIMESTAMP                      |

### Why this table?

Stores the current state of every task.

The Workflow Monitoring module uses task information to compute project KPIs.

### Design Decisions

#### Estimated Hours

Entered by the manager during task creation.

This follows the approach used by project management tools such as Jira and Azure DevOps.

---

#### Actual Hours

For the MVP, entered by the employee when marking a task as completed.

Future versions may calculate this automatically using timers or activity tracking.

---

#### Priority

Priority indicates business importance.

Possible values:

- Low
- Medium
- High
- Critical

---

#### Weight

Weight determines how much a completed task contributes to overall project progress.

Example mapping:

| Priority | Weight |
| -------- | ------ |
| Low      | 1      |
| Medium   | 2      |
| High     | 4      |
| Critical | 6      |

Managers may optionally override these values in future versions.

Workflow Monitoring calculates overall project progress using completed task weights rather than manually entered task percentages, providing a more objective and consistent measure of project completion.

---

## 6. TaskHistory

Stores the history of a task throughout its lifecycle.

### Columns

| Column          | Type            |
| --------------- | --------------- |
| history_id      | UUID (PK)       |
| task_id         | UUID (FK Tasks) |
| updated_by      | UUID (FK Users) |
| change_type     | ENUM            |
| previous_status | ENUM NULL       |
| new_status      | ENUM NULL       |
| remarks         | TEXT NULL       |
| updated_at      | TIMESTAMP       |

### Possible Change Types

- TASK_CREATED
- STATUS_CHANGE
- TASK_COMPLETED
- TASK_REOPENED
- ASSIGNMENT_CHANGE
- PRIORITY_CHANGE
- COMMENT

### Why this table?

Instead of overwriting task information, every important business event is recorded.

Examples:

- Task created
- Task started
- Status changed
- Task completed
- Task reopened
- Assignment changed

This enables:

- Timeline views
- Activity history
- Analytics
- Future ML improvements

### Why not use application logs?

Application logs record technical events.

TaskHistory records business events.

These are two different concepts.

---

## 7. RiskPredictions

Stores historical ML predictions.

### Columns

| Column          | Type               |
| --------------- | ------------------ |
| prediction_id   | UUID (PK)          |
| project_id      | UUID (FK Projects) |
| prediction_time | TIMESTAMP          |
| risk_level      | ENUM               |
| risk_score      | DECIMAL(4,3)       |
| confidence      | DECIMAL(4,3)       |
| model_version   | VARCHAR(30)        |

### Why this table?

The model should not overwrite previous predictions.

Instead, each prediction becomes a historical snapshot.

Example:

```
Week 1 → Low Risk

Week 2 → Medium Risk

Week 3 → High Risk
```

Managers can visualize how project risk changes over time.

Future ML models may add additional fields (e.g., top contributing factors or explanation summaries) without changing the overall design.

---

# Workflow Monitoring (Phase 3)

The Workflow Monitoring module acts as the bridge between Project & Task Management (Phase 2) and the Machine Learning Risk Prediction Engine (Phase 4).

It continuously retrieves project and task data, validates the data, monitors project execution, calculates project health KPIs, aggregates project-level metrics, and transforms these KPIs into standardized numerical features for the Machine Learning model.

## Phase 3 Workflow

```
Phase 2
(Project & Task Management)

        ↓

Data Validation

        ↓

Workflow Monitoring

        ↓

KPI Calculation

        ↓

Feature Engineering

        ↓

Phase 4
Risk Prediction
```

---

## Responsibilities

The Workflow Monitoring module is responsible for:

- Validating project and task data
- Monitoring task status and deadlines
- Automatically detecting overdue tasks
- Calculating project health KPIs
- Aggregating project-level metrics
- Transforming KPIs into standardized ML features
- Providing a consistent feature vector for both model training and live prediction

---

## Generated Features

After validating and analyzing project data, the Workflow Monitoring module calculates a set of standardized Key Performance Indicators (KPIs). These KPIs summarize the current health of a project and serve as input features for the Machine Learning model.

The features are **derived** from the transactional data stored in the database. They are **not permanently stored**, ensuring that the latest project state is always reflected.

| Feature                          | Source              | Description                                                                                                                              |
| -------------------------------- | ------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| Total Tasks                      | Workflow Monitoring | Total number of tasks belonging to the project.                                                                                          |
| Completed Tasks                  | Workflow Monitoring | Number of tasks whose status is **DONE**.                                                                                                |
| Pending Tasks                    | Workflow Monitoring | Number of tasks that have not yet started (**TODO**).                                                                                    |
| In Progress Tasks                | Workflow Monitoring | Number of tasks currently being worked on (**IN_PROGRESS**).                                                                             |
| Project Progress (%)             | Workflow Monitoring | Percentage of project completion calculated using completed task weights divided by the total task weights.                              |
| Overdue Tasks                    | Workflow Monitoring | Number of tasks whose deadline has passed but are not yet completed.                                                                     |
| Delay Percentage                 | Workflow Monitoring | Percentage of project tasks that are currently overdue.                                                                                  |
| Average Delay Days               | Workflow Monitoring | Average number of days overdue across all delayed tasks.                                                                                 |
| Employee Workload Score          | Workflow Monitoring | Workload indicator calculated using the number of active tasks and/or estimated active work hours assigned to employees.                 |
| Estimated Total Hours            | Workflow Monitoring | Sum of the estimated effort for all project tasks.                                                                                       |
| Actual Total Hours               | Workflow Monitoring | Sum of the actual effort recorded for completed tasks.                                                                                   |
| Effort Overrun Percentage        | Workflow Monitoring | Percentage difference between estimated and actual effort, indicating whether the project is exceeding its planned effort.               |
| High Priority Pending Percentage | Workflow Monitoring | Percentage of pending tasks marked as **High** or **Critical** priority.                                                                 |
| Project Age (Days)               | Workflow Monitoring | Number of days elapsed since the project's start date. This value is calculated from the current date and is not stored in the database. |
| Team Size                        | Workflow Monitoring | Number of employees currently assigned to the project, calculated from the ProjectMembers table.                                         |
| Average Task Completion Time     | Workflow Monitoring | Average duration required to complete tasks from their start date to completion date.                                                    |

These generated features collectively represent the current health of the project. Rather than exposing raw database records to the Machine Learning model, Workflow Monitoring aggregates and transforms the data into a consistent, project-level representation that is suitable for prediction.

---

## Phase 3 → Phase 4 Feature Vector

The output of Phase 3 is a standardized **project-level feature vector**. This acts as the data contract between the Workflow Monitoring module (Phase 3) and the Machine Learning Risk Prediction Engine (Phase 4).

Using a fixed feature structure ensures that:

- The same feature definitions are used during both model training and live prediction.
- The Workflow Monitoring and Machine Learning modules remain loosely coupled.
- Future ML models can be updated without modifying the database schema or Workflow Monitoring logic.

### Example Feature Vector

```json
{
  "project_id": "P001",
  "total_tasks": 50,
  "completed_tasks": 36,
  "pending_tasks": 8,
  "in_progress_tasks": 6,
  "project_progress_percentage": 72,
  "overdue_task_count": 7,
  "delay_percentage": 14,
  "average_delay_days": 2.33,
  "employee_workload_score": 0.75,
  "estimated_total_hours": 500,
  "actual_total_hours": 650,
  "effort_overrun_percentage": 30,
  "project_age_days": 120,
  "team_size": 8,
  "high_priority_pending_percentage": 40
}
```

### Feature Descriptions

| Feature                          | Description                                                                      |
| -------------------------------- | -------------------------------------------------------------------------------- |
| project_id                       | Unique identifier of the project being evaluated.                                |
| total_tasks                      | Total number of tasks in the project.                                            |
| completed_tasks                  | Number of completed tasks.                                                       |
| pending_tasks                    | Number of tasks that have not yet started.                                       |
| in_progress_tasks                | Number of tasks currently being worked on.                                       |
| project_progress_percentage      | Overall project completion percentage calculated using weighted task completion. |
| overdue_task_count               | Number of tasks that are overdue.                                                |
| delay_percentage                 | Percentage of overdue tasks relative to the total number of tasks.               |
| average_delay_days               | Average number of days overdue across delayed tasks.                             |
| employee_workload_score          | Normalized workload score representing employee workload distribution.           |
| estimated_total_hours            | Total planned effort for the project.                                            |
| actual_total_hours               | Total recorded effort spent on the project.                                      |
| effort_overrun_percentage        | Percentage by which actual effort exceeds or falls below the estimated effort.   |
| project_age_days                 | Number of days since the project started.                                        |
| team_size                        | Number of employees assigned to the project.                                     |
| high_priority_pending_percentage | Percentage of pending tasks with High or Critical priority.                      |

The Machine Learning model consumes this feature vector to predict:

- Risk Level (Low / Medium / High)
- Risk Probability
- Prediction Confidence

This separation ensures that Workflow Monitoring focuses on measuring project health, while the Machine Learning model focuses solely on risk prediction.

---

# Data Flow

1. Manager creates a project.

2. Employees are assigned to the project.

3. Manager creates tasks.

4. Employees update task status.

5. Task changes are recorded in TaskHistory.

6. Workflow Monitoring validates project and task data.

7. Workflow Monitoring calculates project KPIs.

8. Workflow Monitoring generates the standardized ML feature vector.

9. Machine Learning predicts project risk.

10. Dashboards display project progress, workflow analytics, and risk predictions.

---

# Manual ER Diagram Guide

Draw the following entities as rectangles:

- Users
- Projects
- ProjectMembers
- ProjectClients
- Tasks
- TaskHistory
- RiskPredictions

Relationships:

```
Users (1) -------- (M) ProjectMembers

Projects (1) ----- (M) ProjectMembers

Users (1) -------- (M) ProjectClients

Projects (1) ----- (M) ProjectClients

Projects (1) ----- (M) Tasks

Users (1) -------- (M) Tasks (Assigned To)

Tasks (1) -------- (M) TaskHistory

Projects (1) ----- (M) RiskPredictions
```

Mark primary keys as **PK** and foreign keys as **FK**.

---

# Future Scope

The following features are intentionally excluded from the MVP:

- Notification System
- Report Generation
- Audit Logs
- File Attachments
- Milestones
- Task Subtasks
- Automatic Time Tracking
- Expected Progress Tracking
- Experience-based Task Assignment
- AI Task Recommendation Engine
- Integration with GitHub/Jira
- Collaborative Workspace
  - Shared Canvas
  - Whiteboard
  - Sticky Notes
  - Flowcharts
  - Shared Documents
  - Meeting Notes
  - Reference Links
