import { apiRequest } from "./api";

export async function getRoleProjects(role, subjectId) {
    const safeRole = String(role || "").toLowerCase();
    const safeId = encodeURIComponent(String(subjectId || "").trim());
    if (!safeId || !["employee", "client"].includes(safeRole)) {
        throw new Error("A valid employee or client ID is required.");
    }
    const result = await apiRequest(`/api/${safeRole}/${safeId}/projects`);
    if (result.success === false) {
        throw new Error(result.message || result.error || "Unable to load projects.");
    }
    return result.projects || [];
}

export async function validateRoleId(role, subjectId) {
    const safeRole = String(role || "").toLowerCase();
    const safeId = encodeURIComponent(String(subjectId || "").trim());
    if (!safeId || !["employee", "client"].includes(safeRole)) {
        throw new Error("Enter a valid ID.");
    }
    const result = await apiRequest(`/api/${safeRole}/${safeId}`);
    if (result.success === false) {
        throw new Error(result.message || result.error || `${safeRole} ID not found.`);
    }
    return result[safeRole];
}
