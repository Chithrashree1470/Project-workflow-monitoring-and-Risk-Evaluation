import { useMemo, useState } from "react";

const MANAGER_STATUSES = ["TO_DO", "IN_PROGRESS", "IN_REVIEW", "CLOSED"];
const EMPLOYEE_STATUS_FLOW = {
    TO_DO: "IN_PROGRESS",
    IN_PROGRESS: "IN_REVIEW",
    IN_REVIEW: null
};

function normalizeId(value) {
    return value === null || value === undefined ? "" : String(value).trim();
}

export default function TaskSection({ tasks = [], predictions = {}, role, subjectId, onUpdate, onDelete }) {
    const [loadingTask, setLoadingTask] = useState(null);
    const [message, setMessage] = useState("");
    const normalizedRole = String(role || "").trim().toLowerCase();
    const isManager = normalizedRole === "manager";
    const isEmployee = normalizedRole === "employee";
    const isClient = normalizedRole === "client";
    const employeeId = normalizeId(subjectId);

    const visibleTasks = useMemo(() => {
        if (isEmployee) {
            if (!employeeId) return [];
            return tasks.filter(task => normalizeId(task.assigned_to) === employeeId);
        }
        return isManager || isClient ? tasks : [];
    }, [tasks, isEmployee, isManager, isClient, employeeId]);

    async function updateStatus(taskId, status) {
        if ((!isManager && !isEmployee) || !onUpdate) return;
        try {
            setLoadingTask(taskId); setMessage("");
            await onUpdate(taskId, { status });
            setMessage("Task status updated.");
        } catch (error) {
            setMessage(error.message || "Failed to update task status.");
        } finally { setLoadingTask(null); }
    }

    async function deleteTask(taskId) {
        if (!isManager || !onDelete || !window.confirm("Delete this task?")) return;
        try {
            setLoadingTask(taskId); setMessage("");
            await onDelete(taskId);
            setMessage("Task deleted.");
        } catch (error) {
            setMessage(error.message || "Failed to delete task.");
        } finally { setLoadingTask(null); }
    }

    const emptyMessage = isEmployee
        ? (!employeeId ? "Employee identity is unavailable. Assigned tasks cannot be loaded." : "No tasks are assigned to you.")
        : (!isManager && !isClient ? "This role does not have permission to view tasks." : "No tasks found for this project.");

    return (
        <section className="project-section">
            <h2>Tasks &amp; Execution Risk ({visibleTasks.length})</h2>
            {message && <p className="section-message" role="status">{message}</p>}
            <div className="table-wrapper">
                <table className="project-table task-table">
                    <thead><tr>
                        <th>Task</th><th>Assignee</th><th>Priority</th><th>Status</th>
                        <th>Deadline</th><th>Estimate</th><th>Actual</th><th>Risk</th>
                        {isManager && <th>Action</th>}
                    </tr></thead>
                    <tbody>
                        {visibleTasks.map(task => {
                            const id = task.task_id;
                            const prediction = predictions[String(id)] || {};
                            const status = String(task.status || "TO_DO").toUpperCase();
                            const nextStatus = EMPLOYEE_STATUS_FLOW[status];
                            return <tr key={id}>
                                <td><strong>{task.title || "Untitled"}</strong>{task.description && <small>{task.description}</small>}</td>
                                <td>{task.assigned_to || "Unassigned"}</td>
                                <td>{task.priority || "—"}</td>
                                <td>{isClient ? <span>{status.replaceAll("_", " ")}</span>
                                    : isEmployee ? (nextStatus ? <button className="primary-button" disabled={loadingTask === id} onClick={() => updateStatus(id, nextStatus)}>{loadingTask === id ? "Updating..." : `Move to ${nextStatus.replaceAll("_", " ")}`}</button> : <span>{status.replaceAll("_", " ")}</span>)
                                    : isManager ? <select value={MANAGER_STATUSES.includes(status) ? status : "TO_DO"} disabled={loadingTask === id} onChange={e => updateStatus(id, e.target.value)}>{MANAGER_STATUSES.map(value => <option key={value} value={value}>{value.replaceAll("_", " ")}</option>)}</select> : <span>{status.replaceAll("_", " ")}</span>}</td>
                                <td>{task.deadline || "—"}</td><td>{task.estimated_hours ?? "—"}</td><td>{task.actual_hours ?? "—"}</td>
                                <td>{prediction.risk_label || "Not calculated"}{prediction.risk_score != null && <small>{Number(prediction.risk_score).toFixed(2)}</small>}</td>
                                {isManager && <td><button className="danger-button" disabled={loadingTask === id} onClick={() => deleteTask(id)}>Delete</button></td>}
                            </tr>;
                        })}
                        {visibleTasks.length === 0 && <tr><td colSpan={isManager ? 9 : 8}>{emptyMessage}</td></tr>}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
