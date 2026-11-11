
import { useState } from "react";

export default function TeamMembersSection({
    members = [],
    role,
    onAdd,
    onRemove
}) {
    const [employeeId, setEmployeeId] = useState("");
    const [message, setMessage] = useState("");
    const [loading, setLoading] = useState(false);

    async function addEmployee(event) {
        event.preventDefault();

        if (!employeeId.trim()) {
            setMessage("Enter an employee ID.");
            return;
        }

        try {
            setLoading(true);
            setMessage("");

            const result = await onAdd(employeeId.trim());
            setMessage(result.message || "Employee added.");
            setEmployeeId("");
        } catch (error) {
            setMessage(error.message);
        } finally {
            setLoading(false);
        }
    }

    async function removeEmployee(id) {
        if (!window.confirm(`Remove employee ${id} from this project?`)) {
            return;
        }

        try {
            setLoading(true);
            setMessage("");

            const result = await onRemove(id);
            setMessage(result.message || "Employee removed.");
        } catch (error) {
            setMessage(error.message);
        } finally {
            setLoading(false);
        }
    }

    return (
        <section className="project-section">
            <h2>Team Members ({members.length})</h2>

            {role === "manager" && (
                <form className="add-member-form" onSubmit={addEmployee}>
                    <input
                        value={employeeId}
                        onChange={(event) => setEmployeeId(event.target.value)}
                        placeholder="Enter employee ID"
                    />

                    <button type="submit" disabled={loading}>
                        Add Employee
                    </button>
                </form>
            )}

            {message && <p className="section-message">{message}</p>}

            <div className="table-wrapper">
                <table className="project-table">
                    <thead>
                        <tr>
                            <th>Employee ID</th>
                            <th>Name</th>
                            <th>Department</th>
                            {role === "manager" && <th>Action</th>}
                        </tr>
                    </thead>

                    <tbody>
                        {members.map((member) => (
                            <tr key={member.employee_id}>
                                <td>{member.employee_id}</td>
                                <td>
                                    {member.employee_name ||
                                        member.name ||
                                        "—"}
                                </td>
                                <td>{member.department || "—"}</td>

                                {role === "manager" && (
                                    <td>
                                        <button
                                            className="danger-button"
                                            disabled={loading}
                                            onClick={() =>
                                                removeEmployee(member.employee_id)
                                            }
                                        >
                                            Remove
                                        </button>
                                    </td>
                                )}
                            </tr>
                        ))}

                        {members.length === 0 && (
                            <tr>
                                <td colSpan={role === "manager" ? 4 : 3}>
                                    No team members found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}
