import csv
import re

SQL_FILE = r"C:\Users\Admin\Desktop\programming_file\major project\ai-based-workflow-monitoring-system\dataset\TAWOS.sql\TAWOS.sql"

OUTPUT_FILE = r"C:\Users\Admin\Desktop\programming_file\major project\ai-based-workflow-monitoring-system\dataset\tawos_issue.csv"

# ============================================================
# Columns required for our dynamic-risk ML experiments
# ============================================================

KEEP_COLUMNS = [
    "ID",
    "Jira_ID",
    "Issue_Key",
    "Type",
    "Priority",
    "Status",
    "Creation_Date",
    "Estimation_Date",
    "Resolution_Date",
    "Last_Updated",
    "Story_Point",
    "Timespent",
    "In_Progress_Minutes",
    "Total_Effort_Minutes",
    "Resolution_Time_Minutes",
    "Assignee_ID",
    "Project_ID",
    "Sprint_ID"
]


# ============================================================
# Parse MySQL VALUES
# ============================================================

def parse_sql_values(text):
    values = []
    current = []

    in_string = False
    escape = False

    for char in text:

        if escape:
            current.append(char)
            escape = False
            continue

        if char == "\\" and in_string:
            current.append(char)
            escape = True
            continue

        if char == "'":
            in_string = not in_string
            current.append(char)
            continue

        if char == "," and not in_string:
            values.append(clean_value("".join(current)))
            current = []
            continue

        current.append(char)

    values.append(clean_value("".join(current)))

    return values


def clean_value(value):

    value = value.strip()

    if value.upper() == "NULL":
        return ""

    if len(value) >= 2 and value[0] == "'" and value[-1] == "'":
        value = value[1:-1]

    # MySQL escaping
    value = value.replace("\\'", "'")
    value = value.replace('\\"', '"')
    value = value.replace("\\\\", "\\")

    return value


# ============================================================
# Extract individual (...) rows from INSERT statement
# ============================================================

def extract_rows(values_text):

    rows = []

    current = []
    depth = 0
    in_string = False
    escape = False

    for char in values_text:

        if escape:
            current.append(char)
            escape = False
            continue

        if char == "\\" and in_string:
            current.append(char)
            escape = True
            continue

        if char == "'":
            in_string = not in_string
            current.append(char)
            continue

        if char == "(" and not in_string:

            depth += 1

            if depth == 1:
                current = []
                continue

        if char == ")" and not in_string:

            depth -= 1

            if depth == 0:
                rows.append("".join(current))
                current = []
                continue

        if depth > 0:
            current.append(char)

    return rows


# ============================================================
# Find Issue table definition
# ============================================================

print("=" * 70)
print("SEARCHING FOR ISSUE TABLE")
print("=" * 70)

issue_columns = None

with open(
    SQL_FILE,
    "r",
    encoding="utf-8",
    errors="ignore"
) as f:

    for line in f:

        if re.search(
            r"CREATE TABLE\s+`Issue`\s*\(",
            line,
            re.IGNORECASE
        ):

            print("Found Issue table definition.")

            issue_columns = []

            for line in f:

                line = line.strip()

                if (
                    line.startswith("PRIMARY KEY")
                    or line.startswith("KEY ")
                    or line.startswith("UNIQUE KEY")
                    or line.startswith("CONSTRAINT")
                ):
                    continue

                if line.startswith(")"):
                    break

                match = re.match(r"`([^`]+)`", line)

                if match:
                    issue_columns.append(match.group(1))

            break


if not issue_columns:
    raise Exception(
        "Could not find CREATE TABLE `Issue` in the SQL file."
    )


print("\nColumns found in Issue table:")

for i, column in enumerate(issue_columns):
    print(f"{i}: {column}")


# ============================================================
# Check required columns
# ============================================================

missing = [
    column
    for column in KEEP_COLUMNS
    if column not in issue_columns
]

if missing:

    print("\nWARNING: These columns were not found:")

    for column in missing:
        print(" -", column)

    raise Exception(
        "Required columns are missing. Stop and check the table definition."
    )


column_indexes = [
    issue_columns.index(column)
    for column in KEEP_COLUMNS
]


# ============================================================
# Extract Issue data
# ============================================================

print("\n" + "=" * 70)
print("EXTRACTING ISSUE DATA")
print("=" * 70)

row_count = 0
insert_count = 0

with open(
    SQL_FILE,
    "r",
    encoding="utf-8",
    errors="ignore"
) as f, open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as out:

    writer = csv.writer(out)

    # Write only the columns we need
    writer.writerow(KEEP_COLUMNS)

    for line_number, line in enumerate(f, 1):

        if line_number % 100000 == 0:
            print(
                f"Scanned {line_number:,} lines | "
                f"Rows extracted: {row_count:,}"
            )

        if not re.search(
            r"INSERT INTO\s+`Issue`\s+VALUES",
            line,
            re.IGNORECASE
        ):
            continue

        match = re.search(
            r"INSERT INTO\s+`Issue`\s+VALUES\s*(.*);",
            line,
            re.IGNORECASE
        )

        if not match:
            continue

        insert_count += 1

        values_text = match.group(1)

        rows = extract_rows(values_text)

        for row_text in rows:

            try:

                values = parse_sql_values(row_text)

                if len(values) != len(issue_columns):
                    print(
                        f"Skipping malformed row near line "
                        f"{line_number}: "
                        f"expected {len(issue_columns)} values, "
                        f"got {len(values)}"
                    )
                    continue

                selected = [
                    values[index]
                    for index in column_indexes
                ]

                writer.writerow(selected)

                row_count += 1

            except Exception as e:

                print(
                    f"Could not parse row near line "
                    f"{line_number}: {e}"
                )


# ============================================================
# Finished
# ============================================================

print("\n" + "=" * 70)
print("EXTRACTION COMPLETE")
print("=" * 70)

print(f"INSERT statements processed : {insert_count:,}")
print(f"Rows extracted              : {row_count:,}")
print(f"Output file                 : {OUTPUT_FILE}")

print("=" * 70)