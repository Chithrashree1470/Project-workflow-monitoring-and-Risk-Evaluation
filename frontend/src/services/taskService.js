import { apiRequest } from "./api";

const TASKS_BASE = "/api/tasks";

export function createTask(taskData) {
    return apiRequest(TASKS_BASE, {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(taskData)
    });
}

export function updateTask(taskId, taskData) {
    return apiRequest(
        `${TASKS_BASE}/${encodeURIComponent(taskId)}`,
        {
            method: "PUT",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify(taskData)
        }
    );
}

export function deleteTask(taskId) {
    return apiRequest(
        `${TASKS_BASE}/${encodeURIComponent(taskId)}`,
        {
            method: "DELETE"
        }
    );
}

export function generateProjectRisk(projectId) {
    return apiRequest(
        `${TASKS_BASE}/project/${encodeURIComponent(projectId)}/calculate-risk`,
        {
            method: "POST"
        }
    );
}

export function getAllowedStatuses(role) {
    const normalizedRole = String(role || "").toLowerCase();

    if (normalizedRole === "manager") {
        return ["TO_DO", "IN_PROGRESS", "IN_REVIEW", "CLOSED"];
    }

    if (normalizedRole === "employee") {
        return ["TO_DO", "IN_PROGRESS", "IN_REVIEW"];
    }

    return [];
}

export function canEditTasks(role) {
    return ["manager", "employee"].includes(
        String(role || "").toLowerCase()
    );
}

export function canCloseTask(role) {
    return String(role || "").toLowerCase() === "manager";
}

export function canDeleteTask(role) {
    return String(role || "").toLowerCase() === "manager";
}

export function canGenerateRisk(role) {
    return ["manager", "employee"].includes(
        String(role || "").toLowerCase()
    );
}