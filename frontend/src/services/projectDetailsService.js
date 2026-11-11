import { apiRequest } from "./api";

export function getProjectDetails(projectId) {
    return apiRequest(`/api/project/${projectId}/details`);
}

export function addProjectEmployee(projectId, employeeId) {
    return apiRequest(`/api/project/${projectId}/employees`, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            employee_id: employeeId
        })
    });
}

export function removeProjectEmployee(projectId, employeeId) {
    return apiRequest(
        `/api/project/${projectId}/employees/${employeeId}`,
        {
            method: "DELETE"
        }
    );
}