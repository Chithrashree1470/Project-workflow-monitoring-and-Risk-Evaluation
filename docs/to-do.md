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