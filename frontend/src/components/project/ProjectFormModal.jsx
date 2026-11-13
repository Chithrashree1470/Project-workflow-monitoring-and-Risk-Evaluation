import { useEffect, useState } from "react";
import {
    getEmployee,
    getClient
} from "../../services/projectService";

const INITIAL_PROJECT = {
    Project_Name: "",
    Project_Type: "",
    Project_Budget_USD: "",
    Start_Date: "",
    End_Date: "",
    Project_Manager_Experience: ""
};

const TECHNOLOGIES = [
    "Python",
    "Java",
    "JavaScript",
    "React",
    "Node.js",
    "Flask",
    "Spring Boot",
    "SQL",
    "PostgreSQL",
    "MongoDB",
    "REST API",
    "Docker",
    "AWS",
    "Machine Learning"
];

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

export default function ProjectFormModal({
    isOpen,
    onClose,
    onCreated
}) {
    const [project, setProject] = useState(INITIAL_PROJECT);
    const [technologies, setTechnologies] = useState([]);
    const [customTechnology, setCustomTechnology] = useState("");

    const [employeeId, setEmployeeId] = useState("");
    const [clientId, setClientId] = useState("");

    const [employee, setEmployee] = useState(null);
    const [client, setClient] = useState(null);

    const [lookupError, setLookupError] = useState("");
    const [isSubmitting, setIsSubmitting] = useState(false);

    useEffect(() => {
        if (!isOpen) return;

        function handleEscape(event) {
            if (event.key === "Escape" && !isSubmitting) {
                onClose();
            }
        }

        window.addEventListener("keydown", handleEscape);

        return () => {
            window.removeEventListener("keydown", handleEscape);
        };
    }, [isOpen, isSubmitting, onClose]);

    if (!isOpen) return null;

    function updateField(event) {
        const { name, value } = event.target;

        setProject(previous => ({
            ...previous,
            [name]: value
        }));
    }

    function toggleTechnology(technology) {
        setTechnologies(previous =>
            previous.includes(technology)
                ? previous.filter(item => item !== technology)
                : [...previous, technology]
        );
    }

    function addTechnology() {
        const value = customTechnology.trim();

        if (!value) return;

        setTechnologies(previous =>
            previous.some(
                item => item.toLowerCase() === value.toLowerCase()
            )
                ? previous
                : [...previous, value]
        );

        setCustomTechnology("");
    }

    async function lookupEmployee() {
        setLookupError("");
        setEmployee(null);

        if (!employeeId.trim()) return;

        try {
            const data = await getEmployee(employeeId.trim());

            if (data.success === false || !data.employee) {
                throw new Error(
                    data.error || data.message || "Employee not found."
                );
            }

            setEmployee(data.employee);
        } catch (error) {
            setLookupError(error.message);
        }
    }

    async function lookupClient() {
        setLookupError("");
        setClient(null);

        if (!clientId.trim()) return;

        try {
            const data = await getClient(clientId.trim());

            if (data.success === false || !data.client) {
                throw new Error(
                    data.error || data.message || "Client not found."
                );
            }

            setClient(data.client);
        } catch (error) {
            setLookupError(error.message);
        }
    }

    async function handleSubmit(event) {
        event.preventDefault();

        if (isSubmitting) return;

        if (
            project.Start_Date &&
            project.End_Date &&
            project.End_Date < project.Start_Date
        ) {
            setLookupError("End date cannot be before start date.");
            return;
        }

        if (employeeId.trim() && !employee) {
            setLookupError("Please verify the employee ID first.");
            return;
        }

        if (clientId.trim() && !client) {
            setLookupError("Please verify the client ID first.");
            return;
        }

        setIsSubmitting(true);
        setLookupError("");

        try {
            const formData = new FormData(event.currentTarget);

            // The backend calculates the complexity score automatically.
            formData.delete("Complexity_Score");

            // Submit selected technologies.
            formData.delete("Required_Technology");

            technologies.forEach(technology => {
                formData.append("Required_Technology", technology);
            });

            // These names are read by the existing backend creation workflow.
            if (employee) {
                formData.append("Employee_ID", employeeId.trim());
            }

            if (client) {
                formData.append("Client_ID", clientId.trim());
            }

            const response = await fetch(`${API_BASE_URL}/predict`, {
                method: "POST",
                body: formData,
                credentials: "include",
                headers: {
                    Accept: "application/json"
                }
            });

            const result = await response.json();

            if (!response.ok || result.success === false) {
                throw new Error(
                    result.error ||
                    result.message ||
                    "Project creation failed."
                );
            }

            if (!result.project_id) {
                throw new Error(
                    "Project was created, but the server did not return its project ID."
                );
            }

            // Navigate to the newly created project in the React application.
            onCreated?.(result.project_id);

            onClose();
        } catch (error) {
            setLookupError(
                error.message || "Unable to create project."
            );
        } finally {
            setIsSubmitting(false);
        }
    }

    return (
        <div
            className="project-modal__overlay"
            onMouseDown={event => {
                if (
                    event.target === event.currentTarget &&
                    !isSubmitting
                ) {
                    onClose();
                }
            }}
        >
            <div
                className="project-modal"
                role="dialog"
                aria-modal="true"
                aria-labelledby="project-modal-title"
            >
                <div className="project-modal__header">
                    <div>
                        <h2 id="project-modal-title">
                            Create New Project
                        </h2>

                        <p>
                            Enter project details for the initial risk assessment.
                        </p>
                    </div>

                    <button
                        type="button"
                        className="project-modal__close"
                        onClick={onClose}
                        disabled={isSubmitting}
                        aria-label="Close project form"
                    >
                        ×
                    </button>
                </div>

                <form
                    onSubmit={handleSubmit}
                    className="project-modal__form"
                >
                    <h3>Project Information</h3>

                    <div className="project-modal__grid">
                        <label>
                            Project Name

                            <input
                                name="Project_Name"
                                value={project.Project_Name}
                                onChange={updateField}
                                required
                            />
                        </label>

                        <label>
                            Project Type

                            <select
                                name="Project_Type"
                                value={project.Project_Type}
                                onChange={updateField}
                                required
                            >
                                <option value="">Select type</option>
                                <option value="Web Development">
                                    Web Development
                                </option>
                                <option value="Mobile Application">
                                    Mobile Application
                                </option>
                                <option value="Machine Learning">
                                    Machine Learning
                                </option>
                                <option value="Data Science">
                                    Data Science
                                </option>
                                <option value="Cloud Computing">
                                    Cloud Computing
                                </option>
                                <option value="Other">
                                    Other
                                </option>
                            </select>
                        </label>

                        <label>
                            Project Budget (USD)

                            <input
                                type="number"
                                name="Project_Budget_USD"
                                min="0"
                                step="0.01"
                                value={project.Project_Budget_USD}
                                onChange={updateField}
                                required
                            />
                        </label>

                        <label>
                            Project Manager Experience

                            <input
                                name="Project_Manager_Experience"
                                value={project.Project_Manager_Experience}
                                onChange={updateField}
                                placeholder="Optional"
                            />
                        </label>

                        <label>
                            Start Date

                            <input
                                type="date"
                                name="Start_Date"
                                value={project.Start_Date}
                                onChange={updateField}
                                required
                            />
                        </label>

                        <label>
                            End Date

                            <input
                                type="date"
                                name="End_Date"
                                value={project.End_Date}
                                onChange={updateField}
                                required
                            />
                        </label>
                    </div>

                    <h3>Required Technologies</h3>

                    <div className="project-modal__technologies">
                        {TECHNOLOGIES.map(technology => (
                            <label key={technology}>
                                <input
                                    type="checkbox"
                                    value={technology}
                                    checked={technologies.includes(technology)}
                                    onChange={() => toggleTechnology(technology)}
                                />

                                <span>{technology}</span>
                            </label>
                        ))}
                    </div>

                    <div className="project-modal__lookup">
                        <input
                            placeholder="Add another technology"
                            value={customTechnology}
                            onChange={event =>
                                setCustomTechnology(event.target.value)
                            }
                            onKeyDown={event => {
                                if (event.key === "Enter") {
                                    event.preventDefault();
                                    addTechnology();
                                }
                            }}
                        />

                        <button
                            type="button"
                            onClick={addTechnology}
                        >
                            Add
                        </button>
                    </div>

                    {technologies
                        .filter(technology => !TECHNOLOGIES.includes(technology))
                        .map(technology => (
                            <span
                                className="project-modal__selected-tech"
                                key={technology}
                            >
                                {technology}

                                <button
                                    type="button"
                                    onClick={() => toggleTechnology(technology)}
                                    aria-label={`Remove ${technology}`}
                                >
                                    ×
                                </button>
                            </span>
                        ))}

                    <h3>Team Member Lookup</h3>

                    <div className="project-modal__lookup">
                        <input
                            placeholder="Employee ID"
                            value={employeeId}
                            onChange={event => {
                                setEmployeeId(event.target.value);
                                setEmployee(null);
                            }}
                        />

                        <button
                            type="button"
                            onClick={lookupEmployee}
                            disabled={!employeeId.trim()}
                        >
                            Find Employee
                        </button>
                    </div>

                    {employee && (
                        <div className="project-modal__lookup-result">
                            <strong>{employee.employee_name}</strong>
                            <span>{employee.email}</span>
                            <span>{employee.department}</span>
                            <span className="lookup-verified">
                                Employee verified
                            </span>
                        </div>
                    )}

                    <h3>Client Lookup</h3>

                    <div className="project-modal__lookup">
                        <input
                            placeholder="Client ID"
                            value={clientId}
                            onChange={event => {
                                setClientId(event.target.value);
                                setClient(null);
                            }}
                        />

                        <button
                            type="button"
                            onClick={lookupClient}
                            disabled={!clientId.trim()}
                        >
                            Find Client
                        </button>
                    </div>

                    {client && (
                        <div className="project-modal__lookup-result">
                            <strong>
                                {client.client_name || client.name || clientId}
                            </strong>

                            <span>{client.organization}</span>
                            <span>{client.email}</span>

                            <span className="lookup-verified">
                                Client verified
                            </span>
                        </div>
                    )}

                    {lookupError && (
                        <p className="project-modal__error" role="alert">
                            {lookupError}
                        </p>
                    )}

                    <div className="project-modal__footer">
                        <button
                            type="button"
                            className="project-modal__cancel"
                            onClick={onClose}
                            disabled={isSubmitting}
                        >
                            Cancel
                        </button>

                        <button
                            type="submit"
                            className="project-modal__submit"
                            disabled={isSubmitting}
                        >
                            {isSubmitting
                                ? "Creating Project..."
                                : "Create Project & Generate Risk"}
                        </button>
                    </div>
                </form>
            </div>

            <style>{`
                .project-modal__overlay {
                    position: fixed;
                    inset: 0;
                    z-index: 1000;
                    background: rgba(15, 23, 42, .65);
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    padding: 20px;
                }

                .project-modal {
                    width: min(820px, 100%);
                    max-height: 92vh;
                    overflow-y: auto;
                    background: white;
                    border-radius: 18px;
                    box-shadow: 0 24px 80px rgba(0,0,0,.25);
                }

                .project-modal__header {
                    display: flex;
                    justify-content: space-between;
                    align-items: flex-start;
                    padding: 24px;
                    border-bottom: 1px solid #e2e8f0;
                }

                .project-modal__header h2 {
                    margin: 0 0 6px;
                    color: #0f172a;
                }

                .project-modal__header p {
                    margin: 0;
                    color: #64748b;
                    font-size: 14px;
                }

                .project-modal__close {
                    border: none;
                    background: transparent;
                    font-size: 30px;
                    cursor: pointer;
                    color: #64748b;
                }

                .project-modal__form {
                    padding: 24px;
                }

                .project-modal__form h3 {
                    font-size: 16px;
                    margin: 8px 0 18px;
                    color: #0f172a;
                }

                .project-modal__grid {
                    display: grid;
                    grid-template-columns: repeat(2, minmax(0, 1fr));
                    gap: 16px;
                    margin-bottom: 28px;
                }

                .project-modal__grid label {
                    display: flex;
                    flex-direction: column;
                    gap: 8px;
                    font-size: 13px;
                    font-weight: 600;
                    color: #475569;
                }

                .project-modal__grid input,
                .project-modal__grid select,
                .project-modal__lookup input {
                    width: 100%;
                    box-sizing: border-box;
                    border: 1px solid #cbd5e1;
                    border-radius: 9px;
                    padding: 11px;
                    background: #fff;
                    color: #0f172a;
                    font-size: 14px;
                }

                .project-modal__grid input:focus,
                .project-modal__grid select:focus,
                .project-modal__lookup input:focus {
                    outline: 2px solid #93c5fd;
                    border-color: #2563eb;
                }

                .project-modal__technologies {
                    display: flex;
                    flex-wrap: wrap;
                    gap: 10px;
                    margin-bottom: 15px;
                }

                .project-modal__technologies label {
                    display: flex;
                    align-items: center;
                    gap: 7px;
                    border: 1px solid #cbd5e1;
                    padding: 9px 12px;
                    border-radius: 9px;
                    font-size: 13px;
                    color: #0f172a;
                    background: #ffffff;
                    font-weight: 600;
                    cursor: pointer;
                }

                .project-modal__technologies label span {
                    color: #0f172a;
                }

                .project-modal__technologies input {
                    accent-color: #2563eb;
                }

                .project-modal__lookup {
                    display: flex;
                    gap: 10px;
                    margin-bottom: 18px;
                }

                .project-modal__lookup button {
                    white-space: nowrap;
                    border: 1px solid #2563eb;
                    background: #eff6ff;
                    color: #1d4ed8;
                    border-radius: 9px;
                    padding: 10px 14px;
                    cursor: pointer;
                }

                .project-modal__lookup input::placeholder {
                    color: #64748b;
                    opacity: 1;
                }

                .project-modal__lookup-result {
                    display: flex;
                    flex-direction: column;
                    gap: 5px;
                    padding: 14px;
                    margin-bottom: 20px;
                    background: #f8fafc;
                    color: #334155;
                    border: 1px solid #e2e8f0;
                    border-radius: 9px;
                    font-size: 13px;
                }

                .lookup-verified {
                    color: #15803d;
                    font-weight: 600;
                }

                .project-modal__selected-tech {
                    display: inline-flex;
                    align-items: center;
                    gap: 6px;
                    margin: 0 6px 10px 0;
                    padding: 5px 9px;
                    border-radius: 6px;
                    background: #eff6ff;
                    color: #1e40af;
                    font-size: 12px;
                }

                .project-modal__selected-tech button {
                    border: 0;
                    background: transparent;
                    color: #1e40af;
                    cursor: pointer;
                    font-size: 16px;
                }

                .project-modal__error {
                    color: #b91c1c;
                    background: #fef2f2;
                    padding: 10px;
                    border-radius: 8px;
                    font-size: 13px;
                }

                .project-modal__footer {
                    display: flex;
                    justify-content: flex-end;
                    gap: 12px;
                    padding-top: 20px;
                    border-top: 1px solid #e2e8f0;
                }

                .project-modal__footer button {
                    border-radius: 9px;
                    padding: 12px 18px;
                    font-weight: 600;
                    cursor: pointer;
                }

                .project-modal__footer button:disabled {
                    opacity: .6;
                    cursor: not-allowed;
                }

                .project-modal__cancel {
                    background: white;
                    border: 1px solid #cbd5e1;
                    color: #334155;
                }

                .project-modal__submit {
                    background: #2563eb;
                    border: 1px solid #2563eb;
                    color: white;
                }

                .project-modal__submit:hover:not(:disabled) {
                    background: #1d4ed8;
                }

                @media (max-width: 600px) {
                    .project-modal__grid {
                        grid-template-columns: 1fr;
                    }

                    .project-modal__lookup,
                    .project-modal__footer {
                        flex-direction: column;
                    }
                }
            `}</style>
        </div>
    );
}