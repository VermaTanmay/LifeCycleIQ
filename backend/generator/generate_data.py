
import argparse
import csv
import json
import random
import sqlite3
import hashlib

from pathlib import Path
from datetime import date, timedelta, datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
SCHEMA = Path(__file__).with_name("schema.sql")

FIRST = [
    "Aarav", "Vivaan", "Aditya", "Vihaan", "Arjun",
    "Reyansh", "Sai", "Ishaan", "Krishna", "Rohan",
    "Ananya", "Diya", "Aadhya", "Ira", "Myra",
    "Sara", "Priya", "Kavya", "Meera", "Aanya"
]

LAST = [
    "Sharma", "Verma", "Patel", "Reddy", "Iyer",
    "Gupta", "Nair", "Singh", "Kumar", "Rao",
    "Das", "Mehta", "Shah", "Mishra", "Jain", "Kapoor"
]

DEPARTMENTS = [
    "Engineering", "Human Resources", "Finance", "Sales",
    "Marketing", "Operations", "Customer Success", "Security"
]

ROLES = [
    ("Software Engineer", "STANDARD"),
    ("Senior Software Engineer", "ELEVATED"),
    ("Data Analyst", "STANDARD"),
    ("HR Associate", "STANDARD"),
    ("Finance Analyst", "STANDARD"),
    ("Sales Executive", "STANDARD"),
    ("IT Administrator", "PRIVILEGED"),
    ("Product Manager", "ELEVATED"),
    ("Security Engineer", "PRIVILEGED"),
    ("Support Specialist", "STANDARD"),
    ("DevOps Engineer", "ELEVATED"),
    ("Intern", "STANDARD")
]

SYSTEMS = ["HRIS", "CRM", "ERP", "GITHUB", "CLOUD", "EMAIL"]

TASK_TEMPLATES = [
    ("HR", "DOCUMENTS"),
    ("HR", "ORIENTATION"),
    ("MANAGER", "ORIENTATION"),
    ("IT", "ACCOUNT_SETUP"),
    ("IT", "ACCOUNT_SETUP"),
    ("FACILITIES", "EQUIPMENT"),
    ("FACILITIES", "ACKNOWLEDGEMENT"),
    ("HR", "ACKNOWLEDGEMENT")
]


def iso(value):
    return value.isoformat()


def randdate(rng, start, end):
    return start + timedelta(
        days=rng.randint(0, max(0, (end - start).days))
    )


def dump_csv(conn, table, path):
    cursor = conn.execute(f"SELECT * FROM {table}")

    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([column[0] for column in cursor.description])
        writer.writerows(cursor.fetchall())


def main():

    parser = argparse.ArgumentParser(
        description="LifeCycleIQ synthetic employee lifecycle data generator"
    )

    parser.add_argument(
        "--output",
        default=str(ROOT / "data" / "generated")
    )

    parser.add_argument("--seed", type=int, default=20261022)
    parser.add_argument("--employees", type=int, default=1000)
    parser.add_argument("--tasks", type=int, default=8000)
    parser.add_argument("--grants", type=int, default=1500)
    parser.add_argument("--assets", type=int, default=1200)

    args = parser.parse_args()

    if min(args.employees, args.tasks, args.grants, args.assets) < 1:
        raise SystemExit("All scale values must be >= 1")

    if args.tasks < args.employees:
        raise SystemExit(
            "tasks must be >= employees (at least one onboarding task per employee)"
        )

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    ground_truth_dir = ROOT / "data" / "ground_truth"
    ground_truth_dir.mkdir(parents=True, exist_ok=True)

    db_path = output_dir / "lifecycleiq.db"

    if db_path.exists():
        db_path.unlink()

    rng = random.Random(args.seed)

    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys=ON")

    conn.executescript(
        SCHEMA.read_text(encoding="utf-8")
    )

    # Fixed timestamps ensure deterministic output.
    today = date(2026, 11, 10)
    fixed_timestamp = datetime(
        2026, 11, 10, 12, 0, 0, tzinfo=timezone.utc
    ).isoformat()

    # --------------------------------------------------
    # 1. MASTER DATA
    # --------------------------------------------------

    for index, name in enumerate(DEPARTMENTS, 1):
        conn.execute(
            "INSERT INTO Department VALUES (?,?,?)",
            (
                f"DEPT-{index:03d}",
                name,
                f"CC-{index:04d}"
            )
        )

    for index, (name, tier) in enumerate(ROLES, 1):
        conn.execute(
            "INSERT INTO Role VALUES (?,?,?,1)",
            (
                f"ROLE-{index:03d}",
                name,
                tier
            )
        )

    for index in range(1, 41):

        department = (
            f"DEPT-{((index - 1) % len(DEPARTMENTS)) + 1:03d}"
        )

        manager_name = (
            f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        )

        conn.execute(
            "INSERT INTO Manager VALUES (?,?,?,?)",
            (
                f"MGR-{index:04d}",
                None,
                manager_name,
                department
            )
        )

    for role_index in range(1, len(ROLES) + 1):

        for system in SYSTEMS:

            if role_index in (7, 9) and system in ("CLOUD", "GITHUB"):
                level = "ADMIN"

            elif system in ("HRIS", "EMAIL"):
                level = "WRITE"

            else:
                level = "READ"

            access_role_id = (
                f"AR-{(role_index - 1) * len(SYSTEMS) + SYSTEMS.index(system) + 1:04d}"
            )

            conn.execute(
                "INSERT INTO AccessRole VALUES (?,?,?,?)",
                (
                    access_role_id,
                    f"ROLE-{role_index:03d}",
                    system,
                    level
                )
            )

    # --------------------------------------------------
    # 2. EMPLOYEES AND ONBOARDING
    # --------------------------------------------------

    employee_ids = []
    onboarding_ids = []

    for index in range(1, args.employees + 1):

        employee_id = f"EMP-{index:06d}"
        employee_ids.append(employee_id)

        department_number = rng.randint(1, len(DEPARTMENTS))
        role_number = rng.randint(1, len(ROLES))

        employment_type = rng.choices(
            ["FULL_TIME", "CONTRACTOR", "INTERN"],
            weights=[78, 17, 5]
        )[0]

        end = None

        if index % 47 == 0:

            # Terminated employees must have valid dates.
            hire = today - timedelta(days=rng.randint(40, 180))

            start = hire + timedelta(
                days=rng.choice([0, 0, 0, 1, 3, 7, 14])
            )

            end = today - timedelta(days=rng.randint(1, 20))

            status = "TERMINATED"

        else:

            hire = today - timedelta(days=rng.randint(1, 180))

            start = hire + timedelta(
                days=rng.choice([0, 0, 0, 1, 3, 7, 14])
            )

            status = (
                "ACTIVE" if start <= today else "PREBOARDING"
            )

            if index % 31 == 0:
                status = "ON_LEAVE"

        manager_id = f"MGR-{rng.randint(1, 40):04d}"

        employee_name = (
            f"{rng.choice(FIRST)} {rng.choice(LAST)}"
        )

        conn.execute(
            "INSERT INTO Employee VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (
                employee_id,
                employee_name,
                f"employee{index:06d}@example.test",
                f"DEPT-{department_number:03d}",
                f"ROLE-{role_number:03d}",
                manager_id,
                employment_type,
                status,
                iso(hire),
                iso(start),
                iso(end) if end else None
            )
        )

        onboarding_id = f"ONB-2026-{index:06d}"
        onboarding_ids.append(onboarding_id)

        opened = hire - timedelta(days=rng.randint(0, 3))

        onboarding_status = (
            "COMPLETED"
            if status in ("ACTIVE", "ON_LEAVE", "TERMINATED")
            else "IN_PROGRESS"
        )

        conn.execute(
            "INSERT INTO OnboardingCase VALUES (?,?,?,?,?,?)",
            (
                onboarding_id,
                employee_id,
                onboarding_status,
                iso(opened),
                iso(start),
                None
            )
        )

        # Role history.
        if index % 29 == 0:

            new_role = (
                f"ROLE-{rng.randint(1, len(ROLES)):03d}"
            )

            conn.execute(
                "INSERT INTO RoleHistory VALUES (?,?,?,?,?,?)",
                (
                    f"RH-{index:08d}",
                    employee_id,
                    f"ROLE-{role_number:03d}",
                    new_role,
                    iso(today - timedelta(days=10)),
                    "Synthetic internal role change"
                )
            )

        conn.execute(
            "INSERT INTO AuditEvent VALUES (?,?,?,?,?,?,?)",
            (
                f"EVT-{index:010d}",
                "Employee",
                employee_id,
                "CREATED",
                "SYSTEM",
                fixed_timestamp,
                json.dumps({"seed": args.seed}, sort_keys=True)
            )
        )

    # --------------------------------------------------
    # 3. ONBOARDING TASKS AND DEPENDENCIES
    # --------------------------------------------------

    task_ids_by_case = {}
    task_counter = 0

    for index, employee_id in enumerate(employee_ids, 1):

        onboarding_id = onboarding_ids[index - 1]

        remaining = args.tasks - task_counter
        cases_left = args.employees - index + 1

        task_count = max(1, remaining // cases_left)

        if index == args.employees:
            task_count = remaining

        task_ids = []

        for task_number in range(1, task_count + 1):

            task_counter += 1

            team, task_type = TASK_TEMPLATES[
                (task_number - 1) % len(TASK_TEMPLATES)
            ]

            due_date = today + timedelta(
                days=(task_number % 10) - 2
            )

            task_status = (
                "COMPLETED" if task_number <= 2 else "PENDING"
            )

            task_id = (
                f"TASK-{onboarding_id}-{task_number:03d}"
            )

            task_ids.append(task_id)

            conn.execute(
                "INSERT INTO Task VALUES (?,?,?,?,?,?,?)",
                (
                    task_id,
                    onboarding_id,
                    team,
                    task_type,
                    task_status,
                    iso(due_date),
                    iso(today) if task_status == "COMPLETED" else None
                )
            )

        task_ids_by_case[onboarding_id] = task_ids

        for task_number in range(1, len(task_ids)):

            dependency_id = (
                f"DEP-{(index * 1000 + task_number):08d}"
            )

            conn.execute(
                "INSERT INTO Dependency VALUES (?,?,?)",
                (
                    dependency_id,
                    task_ids[task_number],
                    task_ids[task_number - 1]
                )
            )

    # --------------------------------------------------
    # 4. ACCESS GRANTS
    # --------------------------------------------------

    grant_counts = {}

    for index in range(1, args.grants + 1):

        employee_id = employee_ids[
            (index - 1) % len(employee_ids)
        ]

        employee = conn.execute(
            """
            SELECT role_id, manager_id, start_date, employment_status
            FROM Employee
            WHERE employee_id=?
            """,
            (employee_id,)
        ).fetchone()

        role_id, manager_id, start_date, status = employee

        access_roles = [
            row[0]
            for row in conn.execute(
                "SELECT access_role_id FROM AccessRole WHERE role_id=?",
                (role_id,)
            )
        ]

        access_role_id = access_roles[
            (index - 1) % len(access_roles)
        ]

        sequence = grant_counts.get(employee_id, 0) + 1
        grant_counts[employee_id] = sequence

        grant_id = (
            f"GRANT-{employee_id}-{sequence:03d}"
        )

        requested = (
            datetime(2026, 10, 1, tzinfo=timezone.utc)
            + timedelta(days=index % 40)
        )

        approved = requested + timedelta(hours=2)

        grant_status = (
            "ACTIVE"
            if status in ("ACTIVE", "ON_LEAVE")
            else "REVOKED"
        )

        if status == "TERMINATED":
            grant_status = "REVOKED"

        conn.execute(
            "INSERT INTO AccessGrant VALUES (?,?,?,?,?,?,?,?,?)",
            (
                grant_id,
                employee_id,
                access_role_id,
                grant_status,
                manager_id,
                requested.isoformat(),
                approved.isoformat(),
                start_date,
                None
            )
        )

    # --------------------------------------------------
    # 5. ASSETS AND ASSIGNMENTS
    # --------------------------------------------------

    asset_types = [
        "LAPTOP", "MONITOR", "PHONE", "ACCESS_CARD", "HEADSET"
    ]

    assigned_count = min(
        args.assets,
        max(0, int(args.employees * 0.75))
    )

    for index in range(1, args.assets + 1):

        asset_id = f"AST-{index:06d}"
        asset_type = asset_types[
            (index - 1) % len(asset_types)
        ]

        assigned = index <= assigned_count

        conn.execute(
            "INSERT INTO Asset VALUES (?,?,?,?)",
            (
                asset_id,
                asset_type,
                f"SN-{args.seed}-{index:06d}",
                "ASSIGNED" if assigned else "AVAILABLE"
            )
        )

        if assigned:

            employee_id = employee_ids[
                (index - 1) % len(employee_ids)
            ]

            assignment_status = (
                "ACKNOWLEDGED" if index % 3 else "ASSIGNED"
            )

            conn.execute(
                "INSERT INTO AssetAssignment VALUES (?,?,?,?,?,?,?)",
                (
                    f"ASG-{index:08d}",
                    asset_id,
                    employee_id,
                    assignment_status,
                    iso(today - timedelta(days=index % 30)),
                    (
                        iso(today - timedelta(days=index % 29))
                        if assignment_status == "ACKNOWLEDGED"
                        else None
                    ),
                    None
                )
            )

    # --------------------------------------------------
    # 6. OFFBOARDING CASES
    # --------------------------------------------------

    offboarding_number = 0

    for employee_id in employee_ids:

        employee = conn.execute(
            """
            SELECT employment_status, end_date
            FROM Employee
            WHERE employee_id=?
            """,
            (employee_id,)
        ).fetchone()

        status, end_date = employee

        if status == "TERMINATED":

            offboarding_number += 1

            conn.execute(
                "INSERT INTO OffboardingCase VALUES (?,?,?,?,?,?)",
                (
                    f"OFF-2026-{offboarding_number:06d}",
                    employee_id,
                    "TERMINATION",
                    "IN_PROGRESS",
                    end_date,
                    iso(date.fromisoformat(end_date) - timedelta(days=1))
                )
            )

            conn.execute(
                "INSERT INTO AuditEvent VALUES (?,?,?,?,?,?,?)",
                (
                    f"EVT-{args.employees + offboarding_number:010d}",
                    "OffboardingCase",
                    f"OFF-2026-{offboarding_number:06d}",
                    "CREATED",
                    "SYSTEM",
                    fixed_timestamp,
                    json.dumps({"reason": "TERMINATION"}, sort_keys=True)
                )
            )

    # --------------------------------------------------
    # 7. INJECT FIVE LABELLED ANOMALIES
    # --------------------------------------------------

    labels = []

    # ANOM-001: Access before approval or employee start.
    if args.grants >= 2:

        grant = conn.execute(
            "SELECT grant_id FROM AccessGrant ORDER BY grant_id LIMIT 1"
        ).fetchone()

        grant_id = grant[0]

        conn.execute(
            """
            UPDATE AccessGrant
            SET effective_from='2026-10-01', approved_at=NULL
            WHERE grant_id=?
            """,
            (grant_id,)
        )

        labels.append({
            "issue_id": "ANOM-001",
            "issue_type": "ACCESS_BEFORE_APPROVAL_OR_START",
            "entity_type": "AccessGrant",
            "entity_id": grant_id,
            "expected_detection":
                "Grant is active without approval timestamp or before employee start date"
        })

    # ANOM-002: Duplicate active asset assignment.
    if args.assets >= 2 and args.employees >= 2:

        asset_id = "AST-000001"
        other_employee = employee_ids[1]

        conn.execute(
            "INSERT INTO AssetAssignment VALUES (?,?,?,?,?,?,?)",
            (
                "ASG-99999999",
                asset_id,
                other_employee,
                "ASSIGNED",
                iso(today),
                None,
                None
            )
        )

        labels.append({
            "issue_id": "ANOM-002",
            "issue_type": "DUPLICATE_ACTIVE_ASSET_ASSIGNMENT",
            "entity_type": "Asset",
            "entity_id": asset_id,
            "expected_detection":
                "One asset has multiple active assignments"
        })

    # ANOM-003: Terminated employee retains active access.
    terminated = conn.execute(
        """
        SELECT employee_id
        FROM Employee
        WHERE employment_status='TERMINATED'
        LIMIT 1
        """
    ).fetchone()

    if terminated:

        employee_id = terminated[0]

        access_role_id = conn.execute(
            "SELECT access_role_id FROM AccessRole LIMIT 1"
        ).fetchone()[0]

        sequence = grant_counts.get(employee_id, 0) + 1

        grant_id = (
            f"GRANT-{employee_id}-{sequence:03d}"
        )

        conn.execute(
            "INSERT INTO AccessGrant VALUES (?,?,?,?,?,?,?,?,?)",
            (
                grant_id,
                employee_id,
                access_role_id,
                "ACTIVE",
                None,
                fixed_timestamp,
                None,
                today.isoformat(),
                None
            )
        )

        labels.append({
            "issue_id": "ANOM-003",
            "issue_type": "TERMINATED_EMPLOYEE_ACTIVE_GRANT",
            "entity_type": "AccessGrant",
            "entity_id": grant_id,
            "expected_detection":
                "Active grant exists for terminated employee"
        })

    # ANOM-004: Task dependency cycle.
    cycle = conn.execute(
        """
        SELECT task_id, prerequisite_task_id
        FROM Dependency
        ORDER BY dependency_id
        LIMIT 1
        """
    ).fetchone()

    if cycle:

        first_task, previous_task = cycle

        try:

            conn.execute(
                "INSERT INTO Dependency VALUES (?,?,?)",
                (
                    "DEP-99999999",
                    previous_task,
                    first_task
                )
            )

            labels.append({
                "issue_id": "ANOM-004",
                "issue_type": "TASK_DEPENDENCY_CYCLE",
                "entity_type": "Dependency",
                "entity_id": "DEP-99999999",
                "expected_detection":
                    "Directed task dependency graph contains a cycle"
            })

        except sqlite3.IntegrityError:
            pass

    # ANOM-005: Returned asset still marked assigned.
    recovered = conn.execute(
        """
        SELECT asset_id, employee_id
        FROM AssetAssignment
        WHERE status='ACKNOWLEDGED'
          AND asset_id <> 'AST-000001'
        LIMIT 1
        """
    ).fetchone()

    if recovered:

        asset_id, employee_id = recovered

        conn.execute(
            """
            UPDATE AssetAssignment
            SET status='RETURNED', returned_at=?
            WHERE asset_id=? AND employee_id=?
            """,
            (
                iso(today),
                asset_id,
                employee_id
            )
        )

        labels.append({
            "issue_id": "ANOM-005",
            "issue_type": "RECOVERED_ASSET_STILL_ASSIGNED",
            "entity_type": "Asset",
            "entity_id": asset_id,
            "expected_detection":
                "Asset has returned assignment but current asset status remains ASSIGNED"
        })

    # --------------------------------------------------
    # 8. COMMIT AND EXPORT DATA
    # --------------------------------------------------

    conn.commit()

    tables = [
        "Department",
        "Role",
        "Manager",
        "Employee",
        "OnboardingCase",
        "Task",
        "Dependency",
        "AccessRole",
        "AccessGrant",
        "Asset",
        "AssetAssignment",
        "OffboardingCase",
        "AuditEvent",
        "RoleHistory"
    ]

    for table in tables:

        dump_csv(
            conn,
            table,
            output_dir / f"{table.lower()}.csv"
        )

    with open(
        ground_truth_dir / "ground_truth.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(labels, file, indent=2)

    with open(
        ground_truth_dir / "ground_truth.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=[
                "issue_id",
                "issue_type",
                "entity_type",
                "entity_id",
                "expected_detection"
            ]
        )

        writer.writeheader()
        writer.writerows(labels)

    counts = {
        "employees": args.employees,
        "tasks": task_counter,
        "access_grants": conn.execute(
            "SELECT COUNT(*) FROM AccessGrant"
        ).fetchone()[0],
        "assets": args.assets,
        "anomaly_labels": len(labels)
    }

    manifest = {
        "project": "LifeCycleIQ",
        "seed": args.seed,
        "generated_at_utc": fixed_timestamp,
        "counts": counts,
        "tables": tables,
        "provenance":
            "Synthetic data generated locally; no external personal data."
    }

    (
        output_dir / "source_manifest.json"
    ).write_text(
        json.dumps(manifest, indent=2),
        encoding="utf-8"
    )

    conn.close()

    print(json.dumps(counts, indent=2))
    print(f"Database: {db_path}")
    print(
        f"Ground truth: {ground_truth_dir / 'ground_truth.csv'}"
    )


if __name__ == "__main__":
    main()
