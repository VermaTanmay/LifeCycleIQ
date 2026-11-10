# Architecture

## System boundary

LifeCycleIQ models the employee lifecycle across HR, IT and Facilities. The current stage establishes the relational data foundation and deterministic data-generation pipeline. API orchestration and the React dashboard are added in subsequent stages.

## Entity relationships and cardinality

- Department 1:N Employee
- Role 1:N Employee (current role); Role 1:N AccessRole
- Manager 1:N Employee (manager is optional for top-level employees)
- Employee 1:N OnboardingCase over time; each onboarding case belongs to one employee
- OnboardingCase 1:N Task
- Task N:M Task through Dependency
- Employee 1:N AccessGrant
- AccessRole 1:N AccessGrant
- Employee 1:N AssetAssignment; Asset 1:N AssetAssignment over time
- Employee 1:N OffboardingCase over time
- Employee 1:N AuditEvent (actor employee is optional)
- Employee 1:N RoleHistory

## Lifecycle states

Employee: `PREBOARDING`, `ACTIVE`, `ON_LEAVE`, `TERMINATED`

Onboarding: `DRAFT`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, `CANCELLED`

Task: `PENDING`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, `CANCELLED`

Access grant: `PENDING_APPROVAL`, `ACTIVE`, `REVOKED`, `EXPIRED`, `REJECTED`

Asset: `AVAILABLE`, `ASSIGNED`, `IN_REPAIR`, `RETIRED`

Asset assignment: `ASSIGNED`, `ACKNOWLEDGED`, `RETURNED`, `LOST`

Offboarding: `OPEN`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`

## Effective dates and history

Assignments, grants, role history and offboarding records carry effective dates. Audit events append state changes and preserve the actor, entity, action, timestamp and details. Current-state columns are query conveniences; audit/history tables preserve the transition trail.

## Anomaly model

Known deliberately injected edge cases are labelled in a separate ground-truth file. Operational tables contain the anomaly as a realistic event/record; labels are never copied into operational feature columns. The validator reports the issue and compares detected issues with ground truth.
