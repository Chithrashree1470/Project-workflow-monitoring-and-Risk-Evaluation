We'll implement these in order:
1. projectService.js — existing project and master-data API connections.
2. taskService.js — task operations and risk generation.
3. ProjectRiskPanel.jsx — fixed right-side risk gauge.
4. ProjectTable.jsx and ProjectFormModal.jsx.
5. Manager dashboard.
6. Employee Kanban dashboard.
7. Client read-only dashboard.
8. Connect everything through your existing App.jsx.

Permission audit
Not fully implemented
Requirement	Backend finding	Result
Employee moves TO_DO → IN_PROGRESS → IN_REVIEW	Employees are allowed to update tasks, but there is no validation restricting them to these transitions.	Not enforced
Employee changes IN_REVIEW → CLOSED or back to IN_PROGRESS	The update route accepts CLOSED and other statuses, but does not validate the previous status or allowed transition.	Not enforced
Only manager creates and assigns tasks	create_task() explicitly permits both manager and employee.	Not enforced
Client cannot update tasks	The task create, update and delete routes reject roles other than manager or employee.	Enforced on these routes
Only manager can remove tasks	delete_task() permits both manager and employee.	Not enforced
Only manager can add or remove team members	The add/remove employee endpoints have no manager-role check.	Not enforced