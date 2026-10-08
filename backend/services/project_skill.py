from backend.supabase_client import supabase


def normalize_skill(skill):
    """Normalize a skill/technology name for comparison."""
    return " ".join(
        str(skill or "")
        .strip()
        .lower()
        .split()
    )


def parse_skills(skills):
    """
    Convert the employee skills field into a list.

    Supports values such as:
    'Java, Spring Boot, PostgreSQL'
    'Java; Spring Boot; PostgreSQL'
    """
    if not skills:
        return []

    if isinstance(skills, list):
        raw_skills = skills
    else:
        raw_skills = str(skills).replace(";", ",").split(",")

    return [
        skill.strip()
        for skill in raw_skills
        if skill and skill.strip()
    ]


def get_project_technologies(project_id):
    """Get technologies required by the project."""
    response = (
        supabase
        .table("projects")
        .select("required_technologies")
        .eq("id", project_id)
        .limit(1)
        .execute()
    )

    if not response.data:
        raise ValueError(
            f"Project '{project_id}' was not found."
        )

    technologies = response.data[0].get(
        "required_technologies"
    ) or []

    return technologies


def get_project_team_skills(project_id):
    """Get all skills belonging to the current project team."""
    response = (
        supabase
        .table("project_team_members")
        .select("employee_id, skills")
        .eq("project_id", project_id)
        .execute()
    )

    team_members = response.data or []

    all_skills = []

    for member in team_members:
        skills = parse_skills(
            member.get("skills")
        )
        all_skills.extend(skills)

    return all_skills


def calculate_skill_coverage(project_id):
    """
    Calculate project skill coverage and skill gap.

    Coverage:
        covered required technologies / total required technologies

    Skill gap:
        1 - skill coverage
    """

    required_technologies = get_project_technologies(
        project_id
    )

    team_skills = get_project_team_skills(
        project_id
    )

    # Remove empty values and duplicates
    required_technologies = list(dict.fromkeys(
        tech.strip()
        for tech in required_technologies
        if tech and tech.strip()
    ))

    team_skills = list(dict.fromkeys(
        skill.strip()
        for skill in team_skills
        if skill and skill.strip()
    ))

    # Normalized lookup for case-insensitive comparison
    normalized_team_skills = {
        normalize_skill(skill)
        for skill in team_skills
    }

    covered_skills = []
    missing_skills = []

    for technology in required_technologies:
        normalized_technology = normalize_skill(
            technology
        )

        if normalized_technology in normalized_team_skills:
            covered_skills.append(technology)
        else:
            missing_skills.append(technology)

    total_required = len(required_technologies)
    covered_count = len(covered_skills)

    if total_required == 0:
        skill_coverage = 0.0
        skill_gap = 0.0
    else:
        skill_coverage = (
            covered_count / total_required
        )
        skill_gap = 1.0 - skill_coverage

    return {
        "required_skills": required_technologies,
        "team_skills": team_skills,
        "covered_skills": covered_skills,
        "missing_skills": missing_skills,
        "skill_coverage": round(
            skill_coverage,
            4
        ),
        "skill_gap": round(
            skill_gap,
            4
        )
    }


def update_project_skill_metrics(project_id):
    """
    Calculate and save skill coverage and skill gap
    in the projects table.
    """

    result = calculate_skill_coverage(
        project_id
    )

    update_data = {
        "skill_coverage": result["skill_coverage"],
        "skill_gap": result["skill_gap"]
    }

    (
        supabase
        .table("projects")
        .update(update_data)
        .eq("id", project_id)
        .execute()
    )

    print(
        f"[SKILL METRICS] project_id={project_id}, "
        f"coverage={result['skill_coverage']}, "
        f"gap={result['skill_gap']}"
    )

    return result

from backend.services.project_skill import (
    calculate_skill_coverage
)

if __name__ == "__main__":
    result = calculate_skill_coverage(50)
    print(result)