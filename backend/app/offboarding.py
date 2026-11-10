
import json
from datetime import datetime, timezone
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .database import get_connection, fetch_one, fetch_all

router = APIRouter(tags=["Offboarding Workflow"])


class OffboardingTaskUpdate(BaseModel):
    status: Literal["PENDING", "IN_PROGRESS", "BLOCKED", "COMPLETED", "CANCELLED"]
    actor: str = "HR_ADMIN"


def now():
    return datetime.now(timezone.utc).isoformat()


def ensure_table():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS OffboardingTask (
                task_id TEXT PRIMARY KEY,
                offboarding_id TEXT NOT NULL,
                employee_id TEXT NOT NULL,
                owner_team TEXT NOT NULL,
                task_type TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'PENDING',
                created_at TEXT NOT NULL,
                completed_at TEXT,
                UNIQUE(offboarding_id, task_type),
                FOREIGN KEY (offboarding_id)
                    REFERENCES OffboardingCase(offboarding_id),
                FOREIGN KEY (employee_id)
                    REFERENCES Employee(employee_id)
            )
        """)


ensure_table()


@router.get("/api/offboarding/tasks")
def list_offboarding_tasks(offboarding_id: str | None = None):
    query = """
        SELECT * FROM OffboardingTask
    """
    params = ()

    if offboarding_id:
        query += " WHERE offboarding_id = ?"
        params = (offboarding_id,)

    query += " ORDER BY created_at DESC"
    return fetch_all(query, params)


@router.post("/api/offboarding/{offboarding_id}/start")
def start_offboarding(offboarding_id: str):
    case = fetch_one(
        "SELECT * FROM OffboardingCase WHERE offboarding_id = ?",
        (offboarding_id,)
    )

    if not case:
        raise HTTPException(status_code=404, detail="Offboarding case not found")

    employee_id = case["employee_id"]
    timestamp = now()

    with get_connection() as conn:
        tasks = [
            ("HR", "HR_EXIT_CLEARANCE"),
            ("IT", "IT_ACCESS_REVOCATION"),
            ("FACILITIES", "FACILITIES_ASSET_RETURN"),
        ]

        created = []

        for team, task_type in tasks:
            task_id = f"OFT-{uuid4().hex[:12].upper()}"

            conn.execute("""
                INSERT OR IGNORE INTO OffboardingTask
                (task_id, offboarding_id, employee_id, owner_team,
                 task_type, status, created_at)
                VALUES (?, ?, ?, ?, ?, 'PENDING', ?)
            """, (
                task_id, offboarding_id, employee_id,
                team, task_type, timestamp
            ))

        # Terminate employee and set the exit date.
        conn.execute("""
            UPDATE Employee
            SET employment_status = 'TERMINATED',
                end_date = COALESCE(end_date, ?)
            WHERE employee_id = ?
        """, (case["last_working_date"], employee_id))

        # Revoke active access immediately.
        revoked = conn.execute("""
            UPDATE AccessGrant
            SET status = 'REVOKED',
                effective_to = ?
            WHERE employee_id = ?
              AND status = 'ACTIVE'
        """, (timestamp, employee_id)).rowcount

        # Reject access requests that were not yet approved.
        rejected = conn.execute("""
            UPDATE AccessGrant
            SET status = 'REJECTED'
            WHERE employee_id = ?
              AND status = 'PENDING_APPROVAL'
        """, (employee_id,)).rowcount

        # Mark IT task complete after access has been revoked.
        conn.execute("""
            UPDATE OffboardingTask
            SET status = 'COMPLETED', completed_at = ?
            WHERE offboarding_id = ?
              AND task_type = 'IT_ACCESS_REVOCATION'
        """, (timestamp, offboarding_id))

        # Complete facilities task only if no equipment remains assigned.
        active_assets = conn.execute("""
            SELECT COUNT(*)
            FROM AssetAssignment
            WHERE employee_id = ?
              AND status IN ('ASSIGNED', 'ACKNOWLEDGED')
        """, (employee_id,)).fetchone()[0]

        if active_assets == 0:
            conn.execute("""
                UPDATE OffboardingTask
                SET status = 'COMPLETED', completed_at = ?
                WHERE offboarding_id = ?
                  AND task_type = 'FACILITIES_ASSET_RETURN'
            """, (timestamp, offboarding_id))

        conn.execute("""
            UPDATE OffboardingCase
            SET status = 'IN_PROGRESS'
            WHERE offboarding_id = ?
        """, (offboarding_id,))

        conn.execute("""
            INSERT INTO AuditEvent
            (event_id, entity_type, entity_id, action,
             actor, event_time, details_json)
            VALUES (?, 'OFFBOARDING', ?, 'OFFBOARDING_STARTED',
                    'SYSTEM', ?, ?)
        """, (
            f"AUD-{uuid4().hex[:12].upper()}",
            offboarding_id,
            timestamp,
            json.dumps({
                "employee_id": employee_id,
                "access_revoked": revoked,
                "pending_access_rejected": rejected,
                "active_assets": active_assets
            })
        ))

        created = conn.execute("""
            SELECT * FROM OffboardingTask
            WHERE offboarding_id = ?
            ORDER BY owner_team
        """, (offboarding_id,)).fetchall()

    return {
        "message": "Offboarding workflow started",
        "offboarding_id": offboarding_id,
        "employee_id": employee_id,
        "access_revoked": revoked,
        "pending_access_rejected": rejected,
        "active_assets_to_return": active_assets,
        "tasks": [dict(row) for row in created]
    }


@router.patch("/api/offboarding/tasks/{task_id}/status")
def update_offboarding_task(
    task_id: str,
    payload: OffboardingTaskUpdate
):
    task = fetch_one(
        "SELECT * FROM OffboardingTask WHERE task_id = ?",
        (task_id,)
    )

    if not task:
        raise HTTPException(status_code=404, detail="Offboarding task not found")

    timestamp = now()

    with get_connection() as conn:
        if payload.status == "COMPLETED":
            if task["task_type"] == "IT_ACCESS_REVOCATION":
                active = conn.execute("""
                    SELECT COUNT(*) FROM AccessGrant
                    WHERE employee_id = ? AND status = 'ACTIVE'
                """, (task["employee_id"],)).fetchone()[0]

                if active:
                    raise HTTPException(
                        status_code=409,
                        detail="Cannot complete IT task: active access grants remain"
                    )

            if task["task_type"] == "FACILITIES_ASSET_RETURN":
                active = conn.execute("""
                    SELECT COUNT(*) FROM AssetAssignment
                    WHERE employee_id = ?
                      AND status IN ('ASSIGNED', 'ACKNOWLEDGED')
                """, (task["employee_id"],)).fetchone()[0]

                if active:
                    raise HTTPException(
                        status_code=409,
                        detail="Cannot complete facilities task: equipment is still assigned"
                    )

        conn.execute("""
            UPDATE OffboardingTask
            SET status = ?,
                completed_at = ?
            WHERE task_id = ?
        """, (
            payload.status,
            timestamp if payload.status == "COMPLETED" else None,
            task_id
        ))

        remaining = conn.execute("""
            SELECT COUNT(*) FROM OffboardingTask
            WHERE offboarding_id = ?
              AND status != 'COMPLETED'
        """, (task["offboarding_id"],)).fetchone()[0]

        case_status = "IN_PROGRESS"

        if remaining == 0:
            conn.execute("""
                UPDATE OffboardingCase
                SET status = 'COMPLETED'
                WHERE offboarding_id = ?
            """, (task["offboarding_id"],))
            case_status = "COMPLETED"

        conn.execute("""
            INSERT INTO AuditEvent
            (event_id, entity_type, entity_id, action,
             actor, event_time, details_json)
            VALUES (?, 'OFFBOARDING_TASK', ?, ?, ?, ?, ?)
        """, (
            f"AUD-{uuid4().hex[:12].upper()}",
            task_id,
            f"TASK_{payload.status}",
            payload.actor,
            timestamp,
            json.dumps({
                "offboarding_id": task["offboarding_id"],
                "employee_id": task["employee_id"]
            })
        ))

    return {
        "message": "Offboarding task updated",
        "task_id": task_id,
        "status": payload.status,
        "offboarding_status": case_status
    }
