
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .database import (
    fetch_all,
    fetch_one,
    fetch_value,
    get_connection,
)
from .offboarding import router as offboarding_router


# =====================================================
# REQUEST MODELS
# =====================================================

class TaskStatusUpdate(BaseModel):
    status: Literal[
        "PENDING",
        "IN_PROGRESS",
        "BLOCKED",
        "COMPLETED",
        "CANCELLED",
    ]
    actor: str = "SYSTEM"


class AccessGrantAction(BaseModel):
    actor: str = "IT_ADMIN"


class AssetAssignmentRequest(BaseModel):
    employee_id: str
    actor: str = "IT_ADMIN"


class AnomalyResolutionRequest(BaseModel):
    anomaly_type: Literal[
        "ACTIVE_GRANT_FOR_TERMINATED",
        "ACTIVE_GRANT_WITHOUT_APPROVAL",
        "ASSET_ASSIGNMENT_CONFLICT",
        "RETURNED_ASSET_STILL_ASSIGNED",
        "TASK_DEPENDENCY_CYCLE",
    ]

    actor: str = "WORKFLOW_ADMIN"
    reason: str

    grant_id: str | None = None
    asset_id: str | None = None
    keep_assignment_id: str | None = None

    task_id: str | None = None
    prerequisite_task_id: str | None = None


# =====================================================
# FASTAPI APPLICATION
# =====================================================

app = FastAPI(
    title="LifeCycleIQ API",
    description="Employee lifecycle and workflow orchestration platform",
    version="1.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(offboarding_router)


# =====================================================
# COMMON AUDIT HELPER
# =====================================================

def write_audit(
    connection,
    entity_type,
    entity_id,
    action,
    actor,
    details,
):
    now = datetime.now(timezone.utc).isoformat()

    connection.execute("""
        INSERT INTO AuditEvent (
            event_id,
            entity_type,
            entity_id,
            action,
            actor,
            event_time,
            details_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        f"AUD-API-{uuid4().hex[:12].upper()}",
        entity_type,
        entity_id,
        action,
        actor,
        now,
        json.dumps(details),
    ))

    return now


# =====================================================
# HOME AND HEALTH
# =====================================================

@app.get("/")
def home():
    return {
        "message": "Welcome to LifeCycleIQ API",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/api/health")
def health():
    try:
        employee_count = fetch_value(
            "SELECT COUNT(*) FROM Employee"
        )

        return {
            "status": "healthy",
            "database": "connected",
            "employees": employee_count,
        }

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# =====================================================
# DASHBOARD
# =====================================================

@app.get("/api/dashboard")
def dashboard():
    employee_count = fetch_value(
        "SELECT COUNT(*) FROM Employee"
    )
    task_count = fetch_value(
        "SELECT COUNT(*) FROM Task"
    )
    grant_count = fetch_value(
        "SELECT COUNT(*) FROM AccessGrant"
    )
    asset_count = fetch_value(
        "SELECT COUNT(*) FROM Asset"
    )
    onboarding_count = fetch_value(
        "SELECT COUNT(*) FROM OnboardingCase"
    )
    offboarding_count = fetch_value(
        "SELECT COUNT(*) FROM OffboardingCase"
    )

    employee_status = fetch_all("""
        SELECT
            employment_status AS status,
            COUNT(*) AS count
        FROM Employee
        GROUP BY employment_status
    """)

    task_status = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM Task
        GROUP BY status
    """)

    grant_status = fetch_all("""
        SELECT status, COUNT(*) AS count
        FROM AccessGrant
        GROUP BY status
    """)

    asset_status = fetch_all("""
        SELECT
            asset_status AS status,
            COUNT(*) AS count
        FROM Asset
        GROUP BY asset_status
    """)

    return {
        "totals": {
            "employees": employee_count,
            "tasks": task_count,
            "access_grants": grant_count,
            "assets": asset_count,
            "onboarding_cases": onboarding_count,
            "offboarding_cases": offboarding_count,
        },
        "employee_status": employee_status,
        "task_status": task_status,
        "grant_status": grant_status,
        "asset_status": asset_status,
    }


# =====================================================
# EMPLOYEE APIs
# =====================================================

@app.get("/api/employees")
def employees(
    q: str = "",
    status: str = "",
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    query = """
        SELECT
            e.employee_id,
            e.full_name,
            e.email,
            e.employment_type,
            e.employment_status,
            e.hire_date,
            e.start_date,
            e.end_date,
            d.department_name,
            r.role_name,
            m.manager_name
        FROM Employee e
        LEFT JOIN Department d
            ON e.department_id = d.department_id
        LEFT JOIN Role r
            ON e.role_id = r.role_id
        LEFT JOIN Manager m
            ON e.manager_id = m.manager_id
        WHERE 1=1
    """

    params = []

    if q:
        query += """
            AND (
                e.full_name LIKE ?
                OR e.email LIKE ?
                OR e.employee_id LIKE ?
            )
        """
        search = f"%{q}%"
        params.extend([search, search, search])

    if status:
        query += " AND e.employment_status = ?"
        params.append(status.upper())

    query += """
        ORDER BY e.employee_id
        LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])

    return fetch_all(query, tuple(params))


@app.get("/api/employees/{employee_id}")
def employee_detail(employee_id: str):
    employee = fetch_one("""
        SELECT
            e.*,
            d.department_name,
            r.role_name,
            m.manager_name
        FROM Employee e
        LEFT JOIN Department d
            ON e.department_id = d.department_id
        LEFT JOIN Role r
            ON e.role_id = r.role_id
        LEFT JOIN Manager m
            ON e.manager_id = m.manager_id
        WHERE e.employee_id = ?
    """, (employee_id,))

    if not employee:
        raise HTTPException(
            status_code=404,
            detail="Employee not found",
        )

    employee["tasks"] = fetch_all("""
        SELECT
            t.task_id,
            t.task_type,
            t.owner_team,
            t.status,
            t.due_date,
            t.completed_date
        FROM Task t
        JOIN OnboardingCase o
            ON t.onboarding_id = o.onboarding_id
        WHERE o.employee_id = ?
        ORDER BY t.due_date
    """, (employee_id,))

    employee["access_grants"] = fetch_all("""
        SELECT
            g.grant_id,
            g.status,
            g.requested_at,
            g.approved_at,
            ar.system_name,
            ar.access_level
        FROM AccessGrant g
        JOIN AccessRole ar
            ON g.access_role_id = ar.access_role_id
        WHERE g.employee_id = ?
    """, (employee_id,))

    return employee


# =====================================================
# TASK APIs
# =====================================================

@app.get("/api/tasks")
def tasks(
    status: str = "",
    team: str = "",
    limit: int = Query(default=100, ge=1, le=500),
):
    query = """
        SELECT
            t.task_id,
            t.task_type,
            t.owner_team,
            t.status,
            t.due_date,
            t.completed_date,
            o.onboarding_id,
            e.employee_id,
            e.full_name
        FROM Task t
        JOIN OnboardingCase o
            ON t.onboarding_id = o.onboarding_id
        JOIN Employee e
            ON o.employee_id = e.employee_id
        WHERE 1=1
    """

    params = []

    if status:
        query += " AND t.status = ?"
        params.append(status.upper())

    if team:
        query += " AND t.owner_team = ?"
        params.append(team.upper())

    query += " ORDER BY t.due_date LIMIT ?"
    params.append(limit)

    return fetch_all(query, tuple(params))


@app.patch("/api/tasks/{task_id}/status")
def update_task_status(
    task_id: str,
    request: TaskStatusUpdate,
):
    with get_connection() as connection:
        task = connection.execute(
            "SELECT * FROM Task WHERE task_id = ?",
            (task_id,),
        ).fetchone()

        if not task:
            raise HTTPException(404, "Task not found")

        old_status = task["status"]
        new_status = request.status

        if old_status == new_status:
            return {
                "message": "Task already has this status",
                "task_id": task_id,
                "old_status": old_status,
                "new_status": new_status,
            }

        if new_status == "COMPLETED":
            incomplete = connection.execute("""
                SELECT
                    d.prerequisite_task_id,
                    t.status
                FROM Dependency d
                JOIN Task t
                    ON d.prerequisite_task_id = t.task_id
                WHERE d.task_id = ?
                  AND t.status != 'COMPLETED'
            """, (task_id,)).fetchall()

            if incomplete:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "message": "Prerequisite tasks are not completed",
                        "incomplete_prerequisites": [
                            dict(row) for row in incomplete
                        ],
                    },
                )

        now = datetime.now(timezone.utc).isoformat()
        completed_date = (
            now if new_status == "COMPLETED" else None
        )

        connection.execute("""
            UPDATE Task
            SET status = ?, completed_date = ?
            WHERE task_id = ?
        """, (new_status, completed_date, task_id))

        write_audit(
            connection,
            "TASK",
            task_id,
            "TASK_STATUS_UPDATED",
            request.actor,
            {
                "old_status": old_status,
                "new_status": new_status,
            },
        )

        return {
            "message": "Task status updated successfully",
            "task_id": task_id,
            "old_status": old_status,
            "new_status": new_status,
        }


# =====================================================
# ACCESS GRANT APIs
# =====================================================

@app.get("/api/access-grants")
def access_grants(
    status: str = "",
    limit: int = Query(default=100, ge=1, le=500),
):
    query = """
        SELECT
            g.grant_id,
            g.employee_id,
            e.full_name,
            g.status,
            g.requested_at,
            g.approved_at,
            ar.system_name,
            ar.access_level
        FROM AccessGrant g
        JOIN Employee e
            ON g.employee_id = e.employee_id
        JOIN AccessRole ar
            ON g.access_role_id = ar.access_role_id
        WHERE 1=1
    """

    params = []

    if status:
        query += " AND g.status = ?"
        params.append(status.upper())

    query += " ORDER BY g.requested_at DESC LIMIT ?"
    params.append(limit)

    return fetch_all(query, tuple(params))


@app.post("/api/access-grants/{grant_id}/approve")
def approve_access_grant(
    grant_id: str,
    request: AccessGrantAction,
):
    with get_connection() as connection:
        grant = connection.execute("""
            SELECT g.*, e.employment_status
            FROM AccessGrant g
            JOIN Employee e
                ON g.employee_id = e.employee_id
            WHERE g.grant_id = ?
        """, (grant_id,)).fetchone()

        if not grant:
            raise HTTPException(404, "Access grant not found")

        if grant["status"] != "PENDING_APPROVAL":
            raise HTTPException(
                409,
                f"Cannot approve grant with status {grant['status']}",
            )

        if grant["employment_status"] == "TERMINATED":
            raise HTTPException(
                409,
                "Cannot approve access for a terminated employee",
            )

        now = datetime.now(timezone.utc).isoformat()

        connection.execute("""
            UPDATE AccessGrant
            SET status = 'ACTIVE',
                approved_by = ?,
                approved_at = ?,
                effective_from = ?
            WHERE grant_id = ?
        """, (request.actor, now, now, grant_id))

        write_audit(
            connection,
            "ACCESS_GRANT",
            grant_id,
            "ACCESS_GRANT_APPROVED",
            request.actor,
            {
                "old_status": "PENDING_APPROVAL",
                "new_status": "ACTIVE",
            },
        )

        return {
            "message": "Access grant approved successfully",
            "grant_id": grant_id,
            "old_status": "PENDING_APPROVAL",
            "new_status": "ACTIVE",
        }


@app.post("/api/access-grants/{grant_id}/revoke")
def revoke_access_grant(
    grant_id: str,
    request: AccessGrantAction,
):
    with get_connection() as connection:
        grant = connection.execute("""
            SELECT *
            FROM AccessGrant
            WHERE grant_id = ?
        """, (grant_id,)).fetchone()

        if not grant:
            raise HTTPException(404, "Access grant not found")

        if grant["status"] != "ACTIVE":
            raise HTTPException(
                409,
                f"Cannot revoke grant with status {grant['status']}",
            )

        now = datetime.now(timezone.utc).isoformat()

        connection.execute("""
            UPDATE AccessGrant
            SET status = 'REVOKED',
                effective_to = ?
            WHERE grant_id = ?
        """, (now, grant_id))

        write_audit(
            connection,
            "ACCESS_GRANT",
            grant_id,
            "ACCESS_GRANT_REVOKED",
            request.actor,
            {
                "old_status": "ACTIVE",
                "new_status": "REVOKED",
            },
        )

        return {
            "message": "Access grant revoked successfully",
            "grant_id": grant_id,
            "old_status": "ACTIVE",
            "new_status": "REVOKED",
        }


# =====================================================
# ASSET APIs
# =====================================================

@app.get("/api/assets")
def assets(
    status: str = "",
    limit: int = Query(default=100, ge=1, le=500),
):
    query = """
        SELECT
            a.asset_id,
            a.asset_type,
            a.serial_number,
            a.asset_status,
            aa.assignment_id,
            aa.employee_id,
            e.full_name AS assigned_employee,
            aa.status AS assignment_status,
            aa.assigned_at,
            aa.returned_at
        FROM Asset a
        LEFT JOIN AssetAssignment aa
            ON aa.assignment_id = (
                SELECT aa2.assignment_id
                FROM AssetAssignment aa2
                WHERE aa2.asset_id = a.asset_id
                ORDER BY aa2.assigned_at DESC
                LIMIT 1
            )
        LEFT JOIN Employee e
            ON aa.employee_id = e.employee_id
        WHERE 1=1
    """

    params = []

    if status:
        query += " AND a.asset_status = ?"
        params.append(status.upper())

    query += " ORDER BY a.asset_id LIMIT ?"
    params.append(limit)

    return fetch_all(query, tuple(params))


@app.post("/api/assets/{asset_id}/assign")
def assign_asset(
    asset_id: str,
    request: AssetAssignmentRequest,
):
    with get_connection() as connection:
        asset = connection.execute("""
            SELECT *
            FROM Asset
            WHERE asset_id = ?
        """, (asset_id,)).fetchone()

        if not asset:
            raise HTTPException(404, "Asset not found")

        if asset["asset_status"] != "AVAILABLE":
            raise HTTPException(
                409,
                "Asset is not available for assignment",
            )

        employee = connection.execute("""
            SELECT *
            FROM Employee
            WHERE employee_id = ?
        """, (request.employee_id,)).fetchone()

        if not employee:
            raise HTTPException(404, "Employee not found")

        if employee["employment_status"] == "TERMINATED":
            raise HTTPException(
                409,
                "Cannot assign equipment to a terminated employee",
            )

        now = datetime.now(timezone.utc).isoformat()
        assignment_id = f"ASG-API-{uuid4().hex[:12].upper()}"

        connection.execute("""
            INSERT INTO AssetAssignment (
                assignment_id,
                asset_id,
                employee_id,
                status,
                assigned_at,
                acknowledged_at,
                returned_at
            )
            VALUES (?, ?, ?, 'ASSIGNED', ?, NULL, NULL)
        """, (
            assignment_id,
            asset_id,
            request.employee_id,
            now,
        ))

        connection.execute("""
            UPDATE Asset
            SET asset_status = 'ASSIGNED'
            WHERE asset_id = ?
        """, (asset_id,))

        write_audit(
            connection,
            "ASSET",
            asset_id,
            "ASSET_ASSIGNED",
            request.actor,
            {
                "employee_id": request.employee_id,
                "assignment_id": assignment_id,
            },
        )

        return {
            "message": "Asset assigned successfully",
            "assignment_id": assignment_id,
            "asset_id": asset_id,
            "employee_id": request.employee_id,
            "status": "ASSIGNED",
        }


@app.post("/api/assets/assignments/{assignment_id}/return")
def return_asset(
    assignment_id: str,
    request: AccessGrantAction,
):
    with get_connection() as connection:
        assignment = connection.execute("""
            SELECT *
            FROM AssetAssignment
            WHERE assignment_id = ?
        """, (assignment_id,)).fetchone()

        if not assignment:
            raise HTTPException(
                404,
                "Asset assignment not found",
            )

        if assignment["status"] not in (
            "ASSIGNED",
            "ACKNOWLEDGED",
        ):
            raise HTTPException(
                409,
                "This assignment cannot be returned",
            )

        now = datetime.now(timezone.utc).isoformat()

        connection.execute("""
            UPDATE AssetAssignment
            SET status = 'RETURNED',
                returned_at = ?
            WHERE assignment_id = ?
        """, (now, assignment_id))

        other_active = connection.execute("""
            SELECT COUNT(*)
            FROM AssetAssignment
            WHERE asset_id = ?
              AND assignment_id != ?
              AND status IN ('ASSIGNED', 'ACKNOWLEDGED')
        """, (
            assignment["asset_id"],
            assignment_id,
        )).fetchone()[0]

        new_asset_status = (
            "ASSIGNED" if other_active > 0 else "AVAILABLE"
        )

        connection.execute("""
            UPDATE Asset
            SET asset_status = ?
            WHERE asset_id = ?
        """, (
            new_asset_status,
            assignment["asset_id"],
        ))

        write_audit(
            connection,
            "ASSET",
            assignment["asset_id"],
            "ASSET_RETURNED",
            request.actor,
            {
                "assignment_id": assignment_id,
                "employee_id": assignment["employee_id"],
                "other_active_assignments": other_active,
            },
        )

        return {
            "message": "Asset returned successfully",
            "assignment_id": assignment_id,
            "asset_id": assignment["asset_id"],
            "employee_id": assignment["employee_id"],
            "status": "RETURNED",
            "asset_status": new_asset_status,
        }


# =====================================================
# OFFBOARDING CASES
# =====================================================

@app.get("/api/offboarding")
def offboarding(
    status: str = "",
    limit: int = Query(default=100, ge=1, le=500),
):
    query = """
        SELECT
            o.offboarding_id,
            o.employee_id,
            e.full_name,
            e.email,
            o.reason,
            o.status,
            o.last_working_date,
            o.opened_date
        FROM OffboardingCase o
        JOIN Employee e
            ON o.employee_id = e.employee_id
        WHERE 1=1
    """

    params = []

    if status:
        query += " AND o.status = ?"
        params.append(status.upper())

    query += " ORDER BY o.last_working_date DESC LIMIT ?"
    params.append(limit)

    return fetch_all(query, tuple(params))


# =====================================================
# ANOMALY DETECTION
# =====================================================

@app.get("/api/anomalies")
def anomalies():
    results = []

    # 1. Active access for terminated employees
    rows = fetch_all("""
        SELECT
            g.grant_id,
            e.employee_id,
            e.full_name,
            g.status
        FROM AccessGrant g
        JOIN Employee e
            ON g.employee_id = e.employee_id
        WHERE g.status = 'ACTIVE'
          AND e.employment_status = 'TERMINATED'
    """)

    for row in rows:
        results.append({
            "type": "ACTIVE_GRANT_FOR_TERMINATED",
            "severity": "CRITICAL",
            "description": (
                "Terminated employee still has active system access"
            ),
            "record": row,
        })

    # 2. Active access without approval
    rows = fetch_all("""
        SELECT
            grant_id,
            employee_id,
            status,
            approved_at
        FROM AccessGrant
        WHERE status = 'ACTIVE'
          AND approved_at IS NULL
    """)

    for row in rows:
        results.append({
            "type": "ACTIVE_GRANT_WITHOUT_APPROVAL",
            "severity": "HIGH",
            "description": (
                "Active access grant has no approval timestamp"
            ),
            "record": row,
        })

    # 3. Multiple active assignments
    rows = fetch_all("""
        SELECT
            a.asset_id,
            a.asset_type,
            COUNT(*) AS active_assignments
        FROM Asset a
        JOIN AssetAssignment aa
            ON a.asset_id = aa.asset_id
        WHERE aa.status IN ('ASSIGNED', 'ACKNOWLEDGED')
        GROUP BY a.asset_id, a.asset_type
        HAVING COUNT(*) > 1
    """)

    for row in rows:
        results.append({
            "type": "ASSET_ASSIGNMENT_CONFLICT",
            "severity": "HIGH",
            "description": "Asset has multiple active assignments",
            "record": row,
        })

    # 4. Returned equipment incorrectly marked as assigned.
    # Only report if NO active assignment exists for this asset.
    rows = fetch_all("""
        SELECT
            a.asset_id,
            a.asset_type,
            a.asset_status,
            aa.assignment_id,
            aa.employee_id,
            aa.status AS assignment_status
        FROM Asset a
        JOIN AssetAssignment aa
            ON aa.asset_id = a.asset_id
        WHERE aa.status = 'RETURNED'
          AND a.asset_status = 'ASSIGNED'
          AND NOT EXISTS (
              SELECT 1
              FROM AssetAssignment active
              WHERE active.asset_id = a.asset_id
                AND active.status IN ('ASSIGNED', 'ACKNOWLEDGED')
          )
    """)

    for row in rows:
        results.append({
            "type": "RETURNED_ASSET_STILL_ASSIGNED",
            "severity": "MEDIUM",
            "description": (
                "Returned equipment is still marked as assigned"
            ),
            "record": row,
        })

    # 5. Reciprocal task dependency cycles
    rows = fetch_all("""
        SELECT
            d1.task_id,
            d1.prerequisite_task_id
        FROM Dependency d1
        JOIN Dependency d2
          ON d1.task_id = d2.prerequisite_task_id
         AND d1.prerequisite_task_id = d2.task_id
        WHERE d1.task_id < d1.prerequisite_task_id
    """)

    for row in rows:
        results.append({
            "type": "TASK_DEPENDENCY_CYCLE",
            "severity": "HIGH",
            "description": "Two tasks depend on each other",
            "record": row,
        })

    return {
        "total_anomalies": len(results),
        "anomalies": results,
    }


# =====================================================
# ANOMALY INVESTIGATION AND RESOLUTION
# =====================================================

@app.post("/api/anomalies/resolve")
def resolve_anomaly(request: AnomalyResolutionRequest):

    if not request.reason.strip():
        raise HTTPException(
            status_code=400,
            detail="A resolution reason is required",
        )

    now = datetime.now(timezone.utc).isoformat()

    with get_connection() as connection:

        anomaly_type = request.anomaly_type

        # 1. Revoke access for a terminated employee
        if anomaly_type == "ACTIVE_GRANT_FOR_TERMINATED":

            if not request.grant_id:
                raise HTTPException(400, "grant_id is required")

            grant = connection.execute("""
                SELECT g.*, e.employment_status
                FROM AccessGrant g
                JOIN Employee e
                    ON g.employee_id = e.employee_id
                WHERE g.grant_id = ?
            """, (request.grant_id,)).fetchone()

            if not grant:
                raise HTTPException(404, "Access grant not found")

            if grant["employment_status"] != "TERMINATED":
                raise HTTPException(409, "Employee is not terminated")

            if grant["status"] != "ACTIVE":
                raise HTTPException(409, "Access grant is no longer active")

            connection.execute("""
                UPDATE AccessGrant
                SET status = 'REVOKED',
                    effective_to = ?
                WHERE grant_id = ?
            """, (now, request.grant_id))

            write_audit(
                connection,
                "ACCESS_GRANT",
                request.grant_id,
                "ANOMALY_ACCESS_REVOKED",
                request.actor,
                {
                    "reason": request.reason,
                    "employee_id": grant["employee_id"],
                },
            )

        # 2. Revoke active access without approval
        elif anomaly_type == "ACTIVE_GRANT_WITHOUT_APPROVAL":

            if not request.grant_id:
                raise HTTPException(400, "grant_id is required")

            grant = connection.execute("""
                SELECT *
                FROM AccessGrant
                WHERE grant_id = ?
            """, (request.grant_id,)).fetchone()

            if not grant:
                raise HTTPException(404, "Access grant not found")

            if (
                grant["status"] != "ACTIVE"
                or grant["approved_at"] is not None
            ):
                raise HTTPException(
                    409,
                    "This grant no longer matches the anomaly",
                )

            connection.execute("""
                UPDATE AccessGrant
                SET status = 'REVOKED',
                    effective_to = ?
                WHERE grant_id = ?
            """, (now, request.grant_id))

            write_audit(
                connection,
                "ACCESS_GRANT",
                request.grant_id,
                "UNAPPROVED_ACCESS_REVOKED",
                request.actor,
                {
                    "reason": request.reason,
                    "employee_id": grant["employee_id"],
                },
            )

        # 3. Resolve multiple active asset assignments
        elif anomaly_type == "ASSET_ASSIGNMENT_CONFLICT":

            if (
                not request.asset_id
                or not request.keep_assignment_id
            ):
                raise HTTPException(
                    400,
                    "asset_id and keep_assignment_id are required",
                )

            asset = connection.execute("""
                SELECT *
                FROM Asset
                WHERE asset_id = ?
            """, (request.asset_id,)).fetchone()

            if not asset:
                raise HTTPException(404, "Asset not found")

            active = connection.execute("""
                SELECT *
                FROM AssetAssignment
                WHERE asset_id = ?
                  AND status IN ('ASSIGNED', 'ACKNOWLEDGED')
            """, (request.asset_id,)).fetchall()

            active_ids = [
                row["assignment_id"] for row in active
            ]

            if len(active_ids) <= 1:
                raise HTTPException(
                    409,
                    "Asset no longer has multiple active assignments",
                )

            if request.keep_assignment_id not in active_ids:
                raise HTTPException(
                    400,
                    "Selected assignment is not active for this asset",
                )

            closed_ids = []

            for assignment in active:
                assignment_id = assignment["assignment_id"]

                if assignment_id == request.keep_assignment_id:
                    continue

                connection.execute("""
                    UPDATE AssetAssignment
                    SET status = 'RETURNED',
                        returned_at = ?
                    WHERE assignment_id = ?
                """, (now, assignment_id))

                closed_ids.append(assignment_id)

            connection.execute("""
                UPDATE Asset
                SET asset_status = 'ASSIGNED'
                WHERE asset_id = ?
            """, (request.asset_id,))

            write_audit(
                connection,
                "ASSET",
                request.asset_id,
                "ASSET_ASSIGNMENT_CONFLICT_RESOLVED",
                request.actor,
                {
                    "kept_assignment": request.keep_assignment_id,
                    "closed_assignments": closed_ids,
                    "reason": request.reason,
                },
            )

        # 4. Synchronize returned asset status
        elif anomaly_type == "RETURNED_ASSET_STILL_ASSIGNED":

            if not request.asset_id:
                raise HTTPException(400, "asset_id is required")

            asset = connection.execute("""
                SELECT *
                FROM Asset
                WHERE asset_id = ?
            """, (request.asset_id,)).fetchone()

            if not asset:
                raise HTTPException(404, "Asset not found")

            if asset["asset_status"] != "ASSIGNED":
                raise HTTPException(
                    409,
                    "Asset no longer has the reported status",
                )

            active_count = connection.execute("""
                SELECT COUNT(*)
                FROM AssetAssignment
                WHERE asset_id = ?
                  AND status IN ('ASSIGNED', 'ACKNOWLEDGED')
            """, (request.asset_id,)).fetchone()[0]

            new_status = (
                "ASSIGNED" if active_count > 0 else "AVAILABLE"
            )

            connection.execute("""
                UPDATE Asset
                SET asset_status = ?
                WHERE asset_id = ?
            """, (new_status, request.asset_id))

            write_audit(
                connection,
                "ASSET",
                request.asset_id,
                "ASSET_STATUS_SYNCHRONIZED",
                request.actor,
                {
                    "new_status": new_status,
                    "reason": request.reason,
                },
            )

        # 5. Resolve reciprocal task dependency cycle
        elif anomaly_type == "TASK_DEPENDENCY_CYCLE":

            if (
                not request.task_id
                or not request.prerequisite_task_id
            ):
                raise HTTPException(
                    400,
                    "task_id and prerequisite_task_id are required",
                )

            forward = connection.execute("""
                SELECT dependency_id
                FROM Dependency
                WHERE task_id = ?
                  AND prerequisite_task_id = ?
            """, (
                request.task_id,
                request.prerequisite_task_id,
            )).fetchone()

            reverse = connection.execute("""
                SELECT dependency_id
                FROM Dependency
                WHERE task_id = ?
                  AND prerequisite_task_id = ?
            """, (
                request.prerequisite_task_id,
                request.task_id,
            )).fetchone()

            if not forward or not reverse:
                raise HTTPException(
                    409,
                    "The reciprocal dependency cycle no longer exists",
                )

            connection.execute("""
                DELETE FROM Dependency
                WHERE dependency_id = ?
            """, (forward["dependency_id"],))

            write_audit(
                connection,
                "TASK",
                request.task_id,
                "TASK_DEPENDENCY_CYCLE_RESOLVED",
                request.actor,
                {
                    "removed_dependency": request.task_id,
                    "removed_prerequisite": request.prerequisite_task_id,
                    "reason": request.reason,
                },
            )

        return {
            "message": "Anomaly resolved successfully",
            "anomaly_type": anomaly_type,
            "actor": request.actor,
            "resolved_at": now,
        }


# =====================================================
# AUDIT LOG API
# =====================================================

@app.get("/api/audit-events")
def audit_events(
    entity_type: str = "",
    entity_id: str = "",
    limit: int = Query(default=100, ge=1, le=500),
):
    query = """
        SELECT
            event_id,
            entity_type,
            entity_id,
            action,
            actor,
            event_time,
            details_json
        FROM AuditEvent
        WHERE 1=1
    """

    params = []

    if entity_type:
        query += " AND entity_type = ?"
        params.append(entity_type.upper())

    if entity_id:
        query += " AND entity_id = ?"
        params.append(entity_id)

    query += " ORDER BY event_time DESC LIMIT ?"
    params.append(limit)

    events = fetch_all(query, tuple(params))

    for event in events:
        try:
            event["details"] = json.loads(
                event["details_json"]
            )
        except (TypeError, json.JSONDecodeError):
            event["details"] = {}

    return {
        "total": len(events),
        "events": events,
    }
