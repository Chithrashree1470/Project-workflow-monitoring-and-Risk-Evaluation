
import { apiRequest } from "./api";

export function getProjectDetails(projectId, role = "manager", subjectId = null) {
    const params = new URLSearchParams({ view: role });
    if (subjectId) params.set("subject_id", subjectId);

    return apiRequest(
        `/api/project/${encodeURIComponent(projectId)}/details?${params.toString()}`
    );
}

export function updateProjectDetails(projectId, payload) {
    return apiRequest(`/api/project/${encodeURIComponent(projectId)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });
}

export function addProjectEmployee(projectId, employeeId) {
    return apiRequest(`/api/project/${encodeURIComponent(projectId)}/employees`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ employee_id: employeeId })
    });
}

export function removeProjectEmployee(projectId, employeeId) {
    return apiRequest(
        `/api/project/${encodeURIComponent(projectId)}/employees/${encodeURIComponent(employeeId)}`,
        { method: "DELETE" }
    );
}

export function addProjectClient(projectId, clientId) {
    return apiRequest(`/api/project/${encodeURIComponent(projectId)}/clients`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ client_id: clientId })
    });
}

export function removeProjectClient(projectId, clientId) {
    return apiRequest(
        `/api/project/${encodeURIComponent(projectId)}/clients/${encodeURIComponent(clientId)}`,
        { method: "DELETE" }
    );
}
