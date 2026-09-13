import csv
import re

SQL_FILE = r"C:\Users\Admin\Desktop\programming_file\major project\ai-based-workflow-monitoring-system\dataset\TAWOS.sql\TAWOS.sql"

OUTPUT_FILE = r"C:\Users\Admin\Desktop\programming_file\major project\ai-based-workflow-monitoring-system\dataset\tawos_users.csv"


# ============================================================
# Columns we want from User
# ============================================================

KEEP_COLUMNS = [
    "ID",
    "Username",
    "Display_Name",
    "Email",
    "Project_ID"
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

    value = value.replace("\\'", "'")
    value = value.replace('\\"', '"')
    value = value.replace("\\\\", "\\")

    return value


# ============================================================
# Extract (...) rows from INSERT statement
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
# Find User table definition
# ============================================================

print("=" * 70)
print("SEARCHING FOR USER TABLE")
print("=" * 70)

user_columns = None

with open(
    SQL_FILE,
    "r",
    encoding="utf-8",
    errors="ignore"
) as f:

    for line in f:

        if re.search(
            r"CREATE TABLE\s+`User`\s*\(",
            line,
            re.IGNORECASE
        ):

            print("Found User table definition.")

            user_columns = []

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
                    user_columns.append(match.group(1))

            break


if not user_columns:
    raise Exception(
        "Could not find CREATE TABLE `User` in the SQL file."
    )


print("\nColumns found in User table:")

for i, column in enumerate(user_columns):
    print(f"{i}: {column}")


# ============================================================
# Check requested columns
# ============================================================

missing = [
    column
    for column in KEEP_COLUMNS
    if column not in user_columns
]

if missing:

    print("\nWARNING: These requested columns were NOT found:")

    for column in missing:
        print(" -", column)

    print(
        "\nThe script stopped because the actual User table "
        "has different column names."
    )

    raise Exception("Required User columns are missing.")


column_indexes = [
    user_columns.index(column)
    for column in KEEP_COLUMNS
]


# ============================================================
# Extract User data
# ============================================================

print("\n" + "=" * 70)
print("EXTRACTING USER DATA")
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

    writer.writerow(KEEP_COLUMNS)

    for line_number, line in enumerate(f, 1):

        if line_number % 100000 == 0:

            print(
                f"Scanned {line_number:,} lines | "
                f"Users extracted: {row_count:,}"
            )

        if not re.search(
            r"INSERT INTO\s+`User`\s+VALUES",
            line,
            re.IGNORECASE
        ):
            continue

        match = re.search(
            r"INSERT INTO\s+`User`\s+VALUES\s*(.*);",
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

                if len(values) != len(user_columns):

                    print(
                        f"Skipping malformed row near line "
                        f"{line_number}: "
                        f"expected {len(user_columns)} values, "
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
print("USER EXTRACTION COMPLETE")
print("=" * 70)

print(f"INSERT statements processed : {insert_count:,}")
print(f"Users extracted             : {row_count:,}")
print(f"Output file                 : {OUTPUT_FILE}")

print("=" * 70)