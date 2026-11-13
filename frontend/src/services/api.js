const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export async function apiRequest(path, options = {}) {
    const response = await fetch(`${API_BASE_URL}${path}`, {
        ...options,
        credentials: options.credentials || "include",
        headers: {
            Accept: "application/json",
            ...options.headers
        }
    });

    const contentType = response.headers.get("content-type");

    let data;

    if (contentType && contentType.includes("application/json")) {
        data = await response.json();
    } else {
        data = await response.text();
    }

    if (!response.ok) {
        const message =
            typeof data === "object"
                ? data.error || data.message
                : data;

        throw new Error(message || `Request failed: ${response.status}`);
    }

    return data;
}