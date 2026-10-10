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
        raw_skills = (
            str(skills)
            .replace(";", ",")
            .split(",")
        )

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

    technologies = (
        response.data[0].get(
            "required_technologies"
        ) or []
    )

    return technologies


def get_project_team_members(project_id):
    """Get all team members and their skills."""

    response = (
        supabase
        .table("project_team_members")
        .select("employee_id, skills")
        .eq("project_id", project_id)
        .execute()
    )

    return response.data or []


def calculate_skill_coverage(project_id):
    """
    Calculate project skill coverage, skill distribution,
    and skill gap.

    Technology Coverage:
        Number of required technologies available somewhere
        in the team / total required technologies.

    Skill Distribution:
        Average percentage of team members possessing each
        required technology.

    Skill Gap:
        1 - skill distribution.
    """

    required_technologies = get_project_technologies(
        project_id
    )

    team_members = get_project_team_members(
        project_id
    )

    # ---------------------------------------------------------
    # Clean required technologies
    # ---------------------------------------------------------

    required_technologies = list(
        dict.fromkeys(
            tech.strip()
            for tech in required_technologies
            if tech and tech.strip()
        )
    )

    # ---------------------------------------------------------
    # Parse skills for every team member
    # ---------------------------------------------------------

    member_skills = []

    for member in team_members:
        skills = parse_skills(
            member.get("skills")
        )

        normalized_skills = {
            normalize_skill(skill)
            for skill in skills
            if skill and skill.strip()
        }

        member_skills.append(normalized_skills)

    # ---------------------------------------------------------
    # Technology Coverage
    # ---------------------------------------------------------

    covered_skills = []
    missing_skills = []

    # Used only for checking whether a technology exists
    # anywhere in the team.
    normalized_team_skills = set()

    for skills in member_skills:
        normalized_team_skills.update(skills)

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
    else:
        skill_coverage = (
            covered_count / total_required
        )

    # ---------------------------------------------------------
    # Skill Distribution
    # ---------------------------------------------------------

    total_team_members = len(member_skills)

    technology_distribution = {}

    distribution_values = []

    if total_required > 0 and total_team_members > 0:

        for technology in required_technologies:

            normalized_technology = normalize_skill(
                technology
            )

            members_with_skill = sum(
                1
                for skills in member_skills
                if normalized_technology in skills
            )

            technology_coverage = (
                members_with_skill
                / total_team_members
            )

            technology_distribution[technology] = {
                "members_with_skill": members_with_skill,
                "team_size": total_team_members,
                "coverage": round(
                    technology_coverage,
                    4
                )
            }

            distribution_values.append(
                technology_coverage
            )

        skill_distribution = (
            sum(distribution_values)
            / len(distribution_values)
        )

    else:
        skill_distribution = 0.0

    # ---------------------------------------------------------
    # Skill Gap
    # ---------------------------------------------------------

    skill_gap = 1.0 - skill_distribution

    # ---------------------------------------------------------
    # Return metrics
    # ---------------------------------------------------------

    return {
        "required_skills": required_technologies,

        "covered_skills": covered_skills,

        "missing_skills": missing_skills,

        "skill_coverage": round(
            skill_coverage,
            4
        ),

        "skill_distribution": round(
            skill_distribution,
            4
        ),

        "skill_gap": round(
            skill_gap,
            4
        ),

        "technology_distribution": (
            technology_distribution
        )
    }


def update_project_skill_metrics(project_id):
    """
    Calculate and save skill metrics in the projects table.
    """

    result = calculate_skill_coverage(
        project_id
    )

    update_data = {
        "skill_coverage": result["skill_coverage"],
        "skill_gap": result["skill_gap"]
    }

    response = (
        supabase
        .table("projects")
        .update(update_data)
        .eq("id", project_id)
        .select(
            "id, skill_coverage, skill_gap"
        )
        .execute()
    )

    print(
        f"[SKILL METRICS] project_id="
        f"{project_id}"
    )

    print(
        f"[SKILL METRICS] required="
        f"{result['required_skills']}"
    )

    print(
        f"[SKILL METRICS] covered="
        f"{result['covered_skills']}"
    )

    print(
        f"[SKILL METRICS] missing="
        f"{result['missing_skills']}"
    )

    print(
        f"[SKILL METRICS] technology_coverage="
        f"{result['skill_coverage']}"
    )

    print(
        f"[SKILL METRICS] skill_distribution="
        f"{result['skill_distribution']}"
    )

    print(
        f"[SKILL METRICS] skill_gap="
        f"{result['skill_gap']}"
    )

    print(
        f"[SKILL METRICS] technology_distribution="
        f"{result['technology_distribution']}"
    )

    print(
        f"[SKILL METRICS] DATABASE UPDATE="
        f"{response.data}"
    )

    return result


# -------------------------------------------------------------
# Testing
# -------------------------------------------------------------
#
# from backend.services.project_skill import (
#     calculate_skill_coverage
# )
#
# if __name__ == "__main__":
#     result = calculate_skill_coverage(50)
#     print(result)
