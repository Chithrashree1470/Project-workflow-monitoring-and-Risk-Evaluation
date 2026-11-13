
import { useState } from "react";

export default function ClientsSection({
    clients = [],
    role,
    onAdd,
    onRemove
}) {
    const [clientId, setClientId] = useState("");
    const [busy, setBusy] = useState(false);
    const [message, setMessage] = useState("");

    const isManager = role === "manager";

    async function addClient(event) {
        event.preventDefault();
        if (!clientId.trim()) return;

        try {
            setBusy(true);
            setMessage("");
            await onAdd(clientId.trim());
            setClientId("");
            setMessage("Client added to the project.");
        } catch (error) {
            setMessage(error.message || "Unable to add client.");
        } finally {
            setBusy(false);
        }
    }

    async function removeClient(id) {
        if (!window.confirm("Remove this client from the project?")) return;

        try {
            setBusy(true);
            setMessage("");
            await onRemove(id);
            setMessage("Client removed from the project.");
        } catch (error) {
            setMessage(error.message || "Unable to remove client.");
        } finally {
            setBusy(false);
        }
    }

    return (
        <section className="project-section">
            <div className="clients-heading">
                <h2>Clients / Stakeholders ({clients.length})</h2>
            </div>

            {isManager && (
                <form className="client-add-form" onSubmit={addClient}>
                    <input
                        value={clientId}
                        onChange={event => setClientId(event.target.value)}
                        placeholder="Enter Client ID"
                        required
                    />
                    <button type="submit" disabled={busy || !clientId.trim()}>
                        {busy ? "Saving..." : "Add Client"}
                    </button>
                </form>
            )}

            {message && <p role="status">{message}</p>}

            <div className="table-wrapper">
                <table className="project-table">
                    <thead>
                        <tr>
                            <th>Client ID</th>
                            <th>Name</th>
                            <th>Organization</th>
                            <th>Role</th>
                            <th>Email</th>
                            {isManager && <th>Action</th>}
                        </tr>
                    </thead>

                    <tbody>
                        {clients.map(client => (
                            <tr key={client.client_id}>
                                <td>{client.client_id}</td>
                                <td>{client.client_name || "—"}</td>
                                <td>{client.organization || "—"}</td>
                                <td>{client.role || "—"}</td>
                                <td>{client.email || "—"}</td>
                                {isManager && (
                                    <td>
                                        <button
                                            className="client-remove-button"
                                            disabled={busy}
                                            onClick={() => removeClient(client.client_id)}
                                        >
                                            Remove
                                        </button>
                                    </td>
                                )}
                            </tr>
                        ))}

                        {clients.length === 0 && (
                            <tr>
                                <td colSpan={isManager ? 6 : 5}>
                                    No clients or stakeholders found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>

            <style>{`
                .clients-heading{display:flex;justify-content:space-between;align-items:center}
                .client-add-form{display:flex;gap:10px;margin:14px 0}
                .client-add-form input{flex:1;min-width:0;padding:10px;border:1px solid #cbd5e1;border-radius:8px}
                .client-add-form button{padding:10px 14px;border:0;border-radius:8px;background:#2563eb;color:white;font-weight:600;cursor:pointer}
                .client-remove-button{padding:7px 10px;border:1px solid #fecaca;border-radius:7px;background:white;color:#b91c1c;cursor:pointer}
                @media(max-width:520px){.client-add-form{flex-direction:column}}
            `}</style>
        </section>
    );
}
