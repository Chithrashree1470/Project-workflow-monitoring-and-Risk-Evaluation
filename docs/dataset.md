this is how we have got to phase  model

TAWOS 3 GB SQL dump
        │
        ▼
Import TAWOS database into MySQL
        │
        ├── issue table → 458,232 issues
        │
        └── change_log → 9,253,419 history events
        │
        ▼
Select 10 projects
        │
        ▼
Take up to 2,000 issues/project
        │
        ▼
~20,000 issues
        │
        ├── Issue information
        │
        └── Change history
        │
        ▼
Keep resolved issues
        │
        ▼
Reconstruct historical snapshots
        │
        ▼
For each snapshot:
"Only use information that existed up to this date"
        │
        ▼
Calculate final task duration
        │
        ▼
Convert final duration → risk label
        │
        ├── Low
        ├── Medium
        ├── High
        └── Critical
        │
        ▼
27,235 snapshots
7,512 issues
10 projects
        │
        ▼
Phase 1 model
67.55% accuracy