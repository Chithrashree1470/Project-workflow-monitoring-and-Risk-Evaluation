
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
    task_type: "Task",
    sprint: ""
};

function normalizeId(value) {
    return value === null || value === undefined ? "" : String(value).trim();
}

export default function TaskSection({
    tasks = [],
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
        setForm({ ...EMPTY_TASK });
        setMessage("");
        setShowForm(true);
    }

    function startEdit(task) {
        setEditingId(task.task_id);
        setForm({
            ...EMPTY_TASK,
            ...task,
            deadline: task.deadline ? String(task.deadline).slice(0, 10) : "",
            estimated_hours: task.estimated_hours ?? ""
        });
        setMessage("");
        setShowForm(true);
    }

    function closeForm() {
        if (saving) return;
        setShowForm(false);
        setEditingId(null);
        setForm({ ...EMPTY_TASK });
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

        if (!form.estimated_hours || Number(form.estimated_hours) < 0) {
            setMessage("Enter valid estimated hours.");
            return;
        }

        try {
            setSaving(true);
            setMessage("");

            const payload = {
                title: form.title.trim(),
                description: form.description || "",
                assigned_to: form.assigned_to.trim() || null,
                priority: form.priority,
                status: form.status,
                deadline: form.deadline,
                estimated_hours: Number(form.estimated_hours),
                task_type: form.task_type || "Task",
                sprint: form.sprint || ""
            };

            if (editingId) {
                await onUpdate(editingId, payload);
                setMessage("Task updated.");
            } else {
                if (!onCreate) {
                    throw new Error("Task creation is not connected.");
                }
                await onCreate(payload);
                setMessage("Task created.");
            }

            setShowForm(false);
            setEditingId(null);
            setForm({ ...EMPTY_TASK });
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
                <button type="button" disabled={saving}
                    onClick={() => updateStatus(task.task_id, "IN_PROGRESS")}>
                    Start Task
                </button>
            );
        }

        if (status === "IN_PROGRESS") {
            return (
                <button type="button" disabled={saving}
                    onClick={() => updateStatus(task.task_id, "IN_REVIEW")}>
                    Submit for Review
                </button>
            );
        }

        if (status === "IN_REVIEW") {
            return (
                <div className="task-status-actions">
                    <button type="button" disabled={saving}
                        onClick={() => updateStatus(task.task_id, "CLOSED")}>
                        Close Task
                    </button>
                    <button type="button" disabled={saving}
                        onClick={() => updateStatus(task.task_id, "IN_PROGRESS")}>
                        Reopen
                    </button>
                </div>
            );
        }

        return <span>{status.replaceAll("_", " ")}</span>;
    }

    return (
        <section className="project-section task-section">
            <div className="task-section-heading">
                <h2>Tasks ({visibleTasks.length})</h2>

                {isManager && (
                    <button
                        type="button"
                        className="task-primary-button"
                        onClick={startCreate}
                    >
                        + Add Task
                    </button>
                )}
            </div>

            {message && (
                <p className="section-message" role="status">{message}</p>
            )}

            {showForm && isManager && (
                <div
                    className="task-modal-overlay"
                    onMouseDown={event => {
                        if (event.target === event.currentTarget) closeForm();
                    }}
                >
                    <div
                        className="task-modal"
                        role="dialog"
                        aria-modal="true"
                        aria-labelledby="task-modal-title"
                    >
                        <div className="task-modal-header">
                            <div>
                                <h3 id="task-modal-title">
                                    {editingId ? "Edit Task" : "Create Task"}
                                </h3>
                                <p>Enter the task details below.</p>
                            </div>

                            <button
                                type="button"
                                className="task-modal-close"
                                onClick={closeForm}
                                aria-label="Close"
                            >
                                ×
                            </button>
                        </div>

                        <form onSubmit={saveTask} className="task-modal-form">
                            <div className="task-editor-grid">
                                <label>
                                    Task Title
                                    <input
                                        name="title"
                                        value={form.title}
                                        onChange={changeField}
                                        required
                                    />
                                </label>

                                <label>
                                    Assigned Employee ID
                                    <input
                                        name="assigned_to"
                                        value={form.assigned_to || ""}
                                        onChange={changeField}
                                        placeholder="Enter employee ID"
                                    />
                                </label>

                                <label>
                                    Priority
                                    <select name="priority" value={form.priority}
                                        onChange={changeField}>
                                        {["Low", "Medium", "High", "Critical"].map(value =>
                                            <option key={value} value={value}>{value}</option>
                                        )}
                                    </select>
                                </label>

                                <label>
                                    Status
                                    <select name="status" value={form.status}
                                        onChange={changeField}>
                                        {STATUSES.map(value =>
                                            <option key={value} value={value}>
                                                {value.replaceAll("_", " ")}
                                            </option>
                                        )}
                                    </select>
                                </label>

                                <label>
                                    Deadline
                                    <input
                                        type="date"
                                        name="deadline"
                                        value={form.deadline}
                                        onChange={changeField}
                                        required
                                    />
                                </label>

                                <label>
                                    Estimated Hours
                                    <input
                                        type="number"
                                        min="0"
                                        step="0.5"
                                        name="estimated_hours"
                                        value={form.estimated_hours}
                                        onChange={changeField}
                                        required
                                    />
                                </label>

                                <label>
                                    Task Type
                                    <input
                                        name="task_type"
                                        value={form.task_type || ""}
                                        onChange={changeField}
                                    />
                                </label>

                                <label>
                                    Sprint
                                    <input
                                        name="sprint"
                                        value={form.sprint || ""}
                                        onChange={changeField}
                                    />
                                </label>
                            </div>

                            <label className="task-description-field">
                                Description
                                <textarea
                                    name="description"
                                    value={form.description || ""}
                                    onChange={changeField}
                                    rows={3}
                                />
                            </label>

                            <div className="task-modal-actions">
                                <button
                                    type="button"
                                    className="task-cancel-button"
                                    onClick={closeForm}
                                    disabled={saving}
                                >
                                    Cancel
                                </button>

                                <button
                                    type="submit"
                                    className="task-save-button"
                                    disabled={saving}
                                >
                                    {saving
                                        ? "Saving..."
                                        : editingId ? "Save Changes" : "Create Task"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

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
                            {isManager && <th>Actions</th>}
                        </tr>
                    </thead>

                    <tbody>
                        {visibleTasks.map(task => {
                            const id = task.task_id;
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
                                        {isEmployee
                                            ? employeeActions(task)
                                            : <span>{status.replaceAll("_", " ")}</span>}
                                    </td>
                                    <td>{task.deadline || "—"}</td>
                                    <td>{task.estimated_hours ?? "—"}</td>

                                    {isManager && (
                                        <td>
                                            <div className="task-row-actions">
                                                <button type="button" disabled={saving}
                                                    onClick={() => startEdit(task)}>
                                                    Edit
                                                </button>
                                                <button type="button"
                                                    className="task-delete-button"
                                                    disabled={saving}
                                                    onClick={() => removeTask(id)}>
                                                    Delete
                                                </button>
                                            </div>
                                        </td>
                                    )}
                                </tr>
                            );
                        })}

                        {visibleTasks.length === 0 && (
                            <tr>
                                <td colSpan={isManager ? 7 : 6}>
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
                .task-section-heading {
                    display: flex;
                    align-items: center;
                    justify-content: space-between;
                    gap: 12px;
                }

                .task-section-heading h2 {
                    margin: 0;
                }

                .task-primary-button {
                    border: 0;
                    border-radius: 8px;
                    padding: 10px 14px;
                    background: #0284c7;
                    color: #fff;
                    font-weight: 600;
                    cursor: pointer;
                }

                .task-modal-overlay {
                    position: fixed;
                    inset: 0;
                    z-index: 2000;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                    background: rgba(2, 6, 23, .72);
                }

                .task-modal {
                    width: min(760px, 100%);
                    max-height: 90vh;
                    overflow-y: auto;
                    border: 1px solid #dbe3ed;
                    border-radius: 16px;
                    background: #fff;
                    color: #0f172a;
                    box-shadow: 0 24px 80px rgba(0,0,0,.35);
                }

                .task-modal-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    gap: 15px;
                    padding: 22px 24px;
                    border-bottom: 1px solid #e2e8f0;
                }

                .task-modal-header h3 {
                    margin: 0 0 6px;
                    color: #0f172a;
                    font-size: 20px;
                }

                .task-modal-header p {
                    margin: 0;
                    color: #64748b;
                    font-size: 13px;
                }

                .task-modal-close {
                    border: 0;
                    background: transparent;
                    color: #64748b;
                    font-size: 28px;
                    line-height: 1;
                    cursor: pointer;
                }

                .task-modal-form {
                    padding: 24px;
                }

                .task-editor-grid {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 16px;
                }

                .task-editor-grid label,
                .task-description-field {
                    display: flex;
                    flex-direction: column;
                    gap: 7px;
                    color: #334155;
                    font-size: 13px;
                    font-weight: 600;
                }

                .task-editor-grid input,
                .task-editor-grid select,
                .task-description-field textarea {
                    width: 100%;
                    box-sizing: border-box;
                    padding: 11px 12px;
                    border: 1px solid #cbd5e1;
                    border-radius: 8px;
                    background: #fff;
                    color: #0f172a;
                    font: inherit;
                    font-weight: 400;
                }

                .task-description-field {
                    margin-top: 16px;
                }

                .task-description-field textarea {
                    resize: vertical;
                }

                .task-modal-actions {
                    display: flex;
                    justify-content: flex-end;
                    gap: 10px;
                    margin-top: 22px;
                    padding-top: 18px;
                    border-top: 1px solid #e2e8f0;
                }

                .task-modal-actions button {
                    padding: 10px 16px;
                    border-radius: 8px;
                    font-weight: 600;
                    cursor: pointer;
                }

                .task-cancel-button {
                    border: 1px solid #cbd5e1;
                    background: #fff;
                    color: #334155;
                }

                .task-save-button {
                    border: 1px solid #0284c7;
                    background: #0284c7;
                    color: #fff;
                }

                .task-row-actions,
                .task-status-actions {
                    display: flex;
                    gap: 7px;
                    flex-wrap: wrap;
                }

                .task-row-actions button,
                .task-status-actions button,
                .task-table td > button {
                    padding: 7px 10px;
                    border: 1px solid #cbd5e1;
                    border-radius: 7px;
                    background: #fff;
                    color: #334155;
                    cursor: pointer;
                    font-size: 12px;
                }

                .task-row-actions .task-delete-button {
                    border-color: #fecaca;
                    color: #b91c1c;
                }

                .task-table td small {
                    display: block;
                    margin-top: 4px;
                    color: #64748b;
                    white-space: normal;
                }

                @media (max-width: 600px) {
                    .task-editor-grid {
                        grid-template-columns: 1fr;
                    }

                    .task-modal-overlay {
                        padding: 10px;
                    }

                    .task-modal-form {
                        padding: 18px;
                    }

                    .task-modal-actions {
                        flex-direction: column-reverse;
                    }

                    .task-modal-actions button {
                        width: 100%;
                    }
                }
            `}</style>
        </section>
    );
}
