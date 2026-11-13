
import { useMemo, useState } from "react";

const STATUSES = ["TO_DO", "IN_PROGRESS", "IN_REVIEW", "CLOSED"];

const EMPTY_TASK = {
    title: "",
    description: "",
    assigned_to: "",
    priority: "Medium",
    status: "TO_DO",
    deadline: "",
    estimated_hours: "",
    actual_hours: "",
    task_type: "Task",
    sprint: ""
};

function normalizeId(value) {
    return value === null || value === undefined ? "" : String(value).trim();
}

export default function TaskSection({
    tasks = [],
    predictions = {},
    role,
    subjectId,
    onCreate,
    onUpdate,
    onDelete
}) {
    const [showForm, setShowForm] = useState(false);
    const [editingId, setEditingId] = useState(null);
    const [form, setForm] = useState(EMPTY_TASK);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState("");

    const isManager = role === "manager";
    const isEmployee = role === "employee";
    const isClient = role === "client";

    const visibleTasks = useMemo(() => {
        if (isEmployee) {
            const id = normalizeId(subjectId);
            return id
                ? tasks.filter(task => normalizeId(task.assigned_to) === id)
                : [];
        }

        return isManager || isClient ? tasks : [];
    }, [tasks, isEmployee, isManager, isClient, subjectId]);

    function changeField(event) {
        const { name, value } = event.target;
        setForm(previous => ({ ...previous, [name]: value }));
    }

    function startCreate() {
        setEditingId(null);
        setForm(EMPTY_TASK);
        setShowForm(true);
        setMessage("");
    }

    function startEdit(task) {
        setEditingId(task.task_id);
        setForm({
            ...EMPTY_TASK,
            ...task,
            deadline: task.deadline ? String(task.deadline).slice(0, 10) : "",
            estimated_hours: task.estimated_hours ?? "",
            actual_hours: task.actual_hours ?? ""
        });
        setShowForm(true);
        setMessage("");
    }

    async function saveTask(event) {
        event.preventDefault();

        if (!form.title.trim()) {
            setMessage("Task title is required.");
            return;
        }

        if (!form.deadline) {
            setMessage("Task deadline is required.");
            return;
        }

        try {
            setSaving(true);
            setMessage("");

            const payload = {
                ...form,
                title: form.title.trim(),
                assigned_to: form.assigned_to.trim() || null,
                estimated_hours: Number(form.estimated_hours),
                actual_hours: form.actual_hours === "" ? null : Number(form.actual_hours)
            };

            if (editingId) {
                await onUpdate(editingId, payload);
                setMessage("Task updated.");
            } else {
                await onCreate(payload);
                setMessage("Task created.");
            }

            setShowForm(false);
            setEditingId(null);
            setForm(EMPTY_TASK);
        } catch (error) {
            setMessage(error.message || "Unable to save task.");
        } finally {
            setSaving(false);
        }
    }

    async function updateStatus(taskId, status) {
        try {
            setSaving(true);
            setMessage("");
            await onUpdate(taskId, { status });
            setMessage("Task status updated.");
        } catch (error) {
            setMessage(error.message || "Unable to update task status.");
        } finally {
            setSaving(false);
        }
    }

    async function removeTask(taskId) {
        if (!window.confirm("Delete this task?")) return;

        try {
            setSaving(true);
            setMessage("");
            await onDelete(taskId);
            setMessage("Task deleted.");
        } catch (error) {
            setMessage(error.message || "Unable to delete task.");
        } finally {
            setSaving(false);
        }
    }

    function employeeActions(task) {
        const status = String(task.status || "TO_DO").toUpperCase();

        if (status === "TO_DO") {
            return (
                <button disabled={saving} onClick={() => updateStatus(task.task_id, "IN_PROGRESS")}>
                    Start Task
                </button>
            );
        }

        if (status === "IN_PROGRESS") {
            return (
                <button disabled={saving} onClick={() => updateStatus(task.task_id, "IN_REVIEW")}>
                    Submit for Review
                </button>
            );
        }

        if (status === "IN_REVIEW") {
            return (
                <div className="task-status-actions">
                    <button disabled={saving} onClick={() => updateStatus(task.task_id, "CLOSED")}>
                        Close Task
                    </button>
                    <button disabled={saving} onClick={() => updateStatus(task.task_id, "IN_PROGRESS")}>
                        Reopen
                    </button>
                </div>
            );
        }

        return <span>{status.replaceAll("_", " ")}</span>;
    }

    return (
        <section className="project-section">
            <div className="task-section-heading">
                <h2>Tasks &amp; Execution Risk ({visibleTasks.length})</h2>

                {isManager && (
                    <button className="task-primary-button" onClick={startCreate}>
                        + Add Task
                    </button>
                )}
            </div>

            {message && <p className="section-message" role="status">{message}</p>}

            {showForm && isManager && (
                <form className="task-editor" onSubmit={saveTask}>
                    <h3>{editingId ? "Edit Task" : "Create Task"}</h3>

                    <div className="task-editor-grid">
                        <label>
                            Task Title
                            <input name="title" value={form.title} onChange={changeField} required />
                        </label>

                        <label>
                            Assigned Employee ID
                            <input name="assigned_to" value={form.assigned_to || ""} onChange={changeField} />
                        </label>

                        <label>
                            Priority
                            <select name="priority" value={form.priority} onChange={changeField}>
                                {["Low", "Medium", "High", "Critical"].map(value =>
                                    <option key={value}>{value}</option>
                                )}
                            </select>
                        </label>

                        <label>
                            Status
                            <select name="status" value={form.status} onChange={changeField}>
                                {STATUSES.map(value =>
                                    <option key={value} value={value}>{value.replaceAll("_", " ")}</option>
                                )}
                            </select>
                        </label>

                        <label>
                            Deadline
                            <input type="date" name="deadline" value={form.deadline} onChange={changeField} required />
                        </label>

                        <label>
                            Estimated Hours
                            <input type="number" min="0" step="0.5" name="estimated_hours" value={form.estimated_hours} onChange={changeField} required />
                        </label>

                        <label>
                            Actual Hours
                            <input type="number" min="0" step="0.5" name="actual_hours" value={form.actual_hours} onChange={changeField} />
                        </label>

                        <label>
                            Task Type
                            <input name="task_type" value={form.task_type || ""} onChange={changeField} />
                        </label>

                        <label>
                            Sprint
                            <input name="sprint" value={form.sprint || ""} onChange={changeField} />
                        </label>
                    </div>

                    <label className="task-description-field">
                        Description
                        <textarea name="description" value={form.description || ""} onChange={changeField} rows={3} />
                    </label>

                    <div className="task-editor-actions">
                        <button type="button" onClick={() => setShowForm(false)}>Cancel</button>
                        <button type="submit" disabled={saving}>
                            {saving ? "Saving..." : editingId ? "Save Changes" : "Create Task"}
                        </button>
                    </div>
                </form>
            )}

            <div className="table-wrapper">
                <table className="project-table task-table">
                    <thead>
                        <tr>
                            <th>Task</th><th>Assignee</th><th>Priority</th><th>Status</th>
                            <th>Deadline</th><th>Estimate</th><th>Actual</th><th>Risk</th>
                            {isManager && <th>Actions</th>}
                        </tr>
                    </thead>

                    <tbody>
                        {visibleTasks.map(task => {
                            const id = task.task_id;
                            const prediction = predictions[String(id)] || {};
                            const status = String(task.status || "TO_DO").toUpperCase();

                            return (
                                <tr key={id}>
                                    <td>
                                        <strong>{task.title || "Untitled"}</strong>
                                        {task.description && <small>{task.description}</small>}
                                    </td>
                                    <td>{task.assigned_to || "Unassigned"}</td>
                                    <td>{task.priority || "—"}</td>
                                    <td>
                                        {isManager ? (
                                            <span>{status.replaceAll("_", " ")}</span>
                                        ) : isEmployee ? employeeActions(task) : (
                                            <span>{status.replaceAll("_", " ")}</span>
                                        )}
                                    </td>
                                    <td>{task.deadline || "—"}</td>
                                    <td>{task.estimated_hours ?? "—"}</td>
                                    <td>{task.actual_hours ?? "—"}</td>
                                    <td>
                                        {prediction.risk_label || "Not calculated"}
                                        {prediction.risk_score != null && (
                                            <small>{Number(prediction.risk_score).toFixed(2)}</small>
                                        )}
                                    </td>

                                    {isManager && (
                                        <td>
                                            <div className="task-row-actions">
                                                <button disabled={saving} onClick={() => startEdit(task)}>Edit</button>
                                                <button className="task-delete-button" disabled={saving} onClick={() => removeTask(id)}>Delete</button>
                                            </div>
                                        </td>
                                    )}
                                </tr>
                            );
                        })}

                        {visibleTasks.length === 0 && (
                            <tr>
                                <td colSpan={isManager ? 9 : 8}>
                                    {isEmployee
                                        ? "No tasks are assigned to you."
                                        : "No tasks found for this project."}
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <style>{`
                .task-section-heading{display:flex;align-items:center;justify-content:space-between;gap:12px}
                .task-primary-button,.task-editor-actions button:last-child{border:0;border-radius:8px;padding:10px 14px;background:#2563eb;color:#fff;font-weight:600;cursor:pointer}
                .task-editor{margin:16px 0;padding:18px;background:#f8fafc;border:1px solid #dbe3ed;border-radius:12px}
                .task-editor h3{margin:0 0 15px;color:#0f172a}
                .task-editor-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}
                .task-editor label,.task-description-field{display:flex;flex-direction:column;gap:6px;color:#475569;font-size:13px}
                .task-editor input,.task-editor select,.task-editor textarea{width:100%;box-sizing:border-box;padding:10px;border:1px solid #cbd5e1;border-radius:8px;background:#fff;color:#0f172a}
                .task-description-field{margin-top:12px}
                .task-editor-actions,.task-row-actions,.task-status-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
                .task-editor-actions button,.task-row-actions button,.task-status-actions button{border:1px solid #cbd5e1;border-radius:7px;padding:7px 10px;background:#fff;color:#334155;cursor:pointer}
                .task-row-actions .task-delete-button{color:#b91c1c;border-color:#fecaca}
                .task-table td small{display:block;margin-top:4px;color:#64748b;white-space:normal}
                .task-table td button{font-size:12px}
                @media(max-width:600px){.task-editor-grid{grid-template-columns:1fr}.task-section-heading{align-items:flex-start;flex-direction:column}}
            `}</style>
        </section>
    );
}
