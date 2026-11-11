import { useState } from "react";

const MANAGER_STATUSES = [
    "TO_DO",
    "IN_PROGRESS",
    "IN_REVIEW",
    "CLOSED"
];

const EMPLOYEE_STATUSES = [
    "TO_DO",
    "IN_PROGRESS",
    "IN_REVIEW"
];

export default function TaskSection({
    tasks = [],
    predictions = {},
    role,
    onUpdate,
    onDelete
}) {
    const [loadingTask, setLoadingTask] = useState(null);
    const [message, setMessage] = useState("");

    const statuses =
        role === "manager" ? MANAGER_STATUSES : EMPLOYEE_STATUSES;

    async function updateStatus(taskId, status) {
        try {
            setLoadingTask(taskId);
            setMessage("");
            await onUpdate(taskId, { status });
            setMessage("Task status updated.");
        } catch (error) {
            setMessage(error.message);
        } finally {
            setLoadingTask(null);
        }
    }

    async function deleteTask(taskId) {
        if (!window.confirm("Delete this task?")) return;

        try {
            setLoadingTask(taskId);
            setMessage("");
            await onDelete(taskId);
            setMessage("Task deleted.");
        } catch (error) {
            setMessage(error.message);
        } finally {
            setLoadingTask(null);
        }
    }

    return (
        <section className="project-section">
            <h2>Tasks & Execution Risk ({tasks.length})</h2>

            {message && <p className="section-message">{message}</p>}

            <div className="table-wrapper">
                <table className="project-table task-table">
                    <thead>
                        <tr>
                            <th>Task</th>
                            <th>Assignee</th>
                            <th>Priority</th>
                            <th>Status</th>
                            <th>Deadline</th>
                            <th>Estimate</th>
                            <th>Actual</th>
                            <th>Risk</th>
                            {role === "manager" && <th>Action</th>}
                        </tr>
                    </thead>

                    <tbody>
                        {tasks.map((task) => {
                            const prediction =
                                predictions[String(task.task_id)] || {};

                            return (
                                <tr key={task.task_id}>
                                    <td>
                                        <strong>{task.title || "Untitled"}</strong>
                                        {task.description && (
                                            <small>{task.description}</small>
                                        )}
                                    </td>

                                    <td>{task.assigned_to || "Unassigned"}</td>
                                    <td>{task.priority || "—"}</td>

                                    <td>
                                        <select
                                            value={task.status || "TO_DO"}
                                            disabled={loadingTask === task.task_id}
                                            onChange={(e) =>
                                                updateStatus(
                                                    task.task_id,
                                                    e.target.value
                                                )
                                            }
                                        >
                                            {statuses.map((status) => (
                                                <option key={status} value={status}>
                                                    {status.replaceAll("_", " ")}
                                                </option>
                                            ))}
                                        </select>
                                    </td>

                                    <td>{task.deadline || "—"}</td>
                                    <td>{task.estimated_hours ?? "—"}</td>
                                    <td>{task.actual_hours ?? "—"}</td>

                                    <td>
                                        {prediction.risk_label || "Not calculated"}
                                        {prediction.risk_score != null && (
                                            <small>
                                                {Number(prediction.risk_score).toFixed(2)}
                                            </small>
                                        )}
                                    </td>

                                    {role === "manager" && (
                                        <td>
                                            <button
                                                className="danger-button"
                                                disabled={loadingTask === task.task_id}
                                                onClick={() => deleteTask(task.task_id)}
                                            >
                                                Delete
                                            </button>
                                        </td>
                                    )}
                                </tr>
                            );
                        })}

                        {tasks.length === 0 && (
                            <tr>
                                <td colSpan={role === "manager" ? 9 : 8}>
                                    No tasks found for this project.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}