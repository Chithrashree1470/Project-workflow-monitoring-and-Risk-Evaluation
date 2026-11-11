import { apiRequest } from "./api";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export function getEmployee(employeeId) {
    return apiRequest(
        `/api/employee/${encodeURIComponent(employeeId)}`
    );
}

export function getClient(clientId) {
    return apiRequest(
        `/api/client/${encodeURIComponent(clientId)}`
    );
}

export function getCapableEmployees(projectType) {
    return apiRequest(
        `/api/employees/capable?project_type=${encodeURIComponent(projectType)}`
    );
}

export async function createProject(formData) {
    // The existing Flask /predict route returns HTML.
    // Keep native form submission to preserve its current behavior.
    const form = document.createElement("form");

    form.method = "POST";
    form.action = `${API_BASE_URL}/predict`;
    form.enctype = "multipart/form-data";
    form.style.display = "none";

    for (const [name, value] of formData.entries()) {
        if (value instanceof File) {
            throw new Error(
                "File uploads require direct submission from the project form."
            );
        }

        const input = document.createElement("input");
        input.type = "hidden";
        input.name = name;
        input.value = value;
        form.appendChild(input);
    }

    document.body.appendChild(form);
    form.submit();
}

export function getProjectDetailsUrl(projectId) {
    return `/project/${encodeURIComponent(projectId)}`;
}

export function getDashboardUrl() {
    return "/dashboard";
}