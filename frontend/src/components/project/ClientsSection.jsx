export default function ClientsSection({ clients = [] }) {
    return (
        <section className="project-section">
            <h2>Clients / Stakeholders ({clients.length})</h2>

            <div className="table-wrapper">
                <table className="project-table">
                    <thead>
                        <tr>
                            <th>Client ID</th>
                            <th>Name</th>
                            <th>Organization</th>
                            <th>Role</th>
                            <th>Email</th>
                        </tr>
                    </thead>

                    <tbody>
                        {clients.map((client) => (
                            <tr key={client.client_id}>
                                <td>{client.client_id}</td>
                                <td>{client.client_name || "—"}</td>
                                <td>{client.organization || "—"}</td>
                                <td>{client.role || "—"}</td>
                                <td>{client.email || "—"}</td>
                            </tr>
                        ))}

                        {clients.length === 0 && (
                            <tr>
                                <td colSpan={5}>
                                    No clients or stakeholders found.
                                </td>
                            </tr>
                        )}
                    </tbody>
                </table>
            </div>
        </section>
    );
}