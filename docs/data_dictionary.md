# Data Dictionary

Types use SQLite conventions. `PK` = primary key; `FK` = foreign key; `UQ` = unique. All timestamps use ISO-8601 UTC strings; all dates use `YYYY-MM-DD`.

| Entity | Field | Type | Required | Allowed values / validation |
|---|---|---:|---|---|
| Employee | employee_id | TEXT PK | Yes | `EMP-` + six digits; immutable |
| Employee | full_name | TEXT | Yes | Synthetic name, non-empty |
| Employee | email | TEXT UQ | Yes | Unique `@example.test` address |
| Employee | department_id | TEXT FK | Yes | Existing Department |
| Employee | role_id | TEXT FK | Yes | Existing Role |
| Employee | manager_id | TEXT FK | No | Existing Manager; nullable |
| Employee | employment_type | TEXT | Yes | `FULL_TIME`, `CONTRACTOR`, `INTERN` |
| Employee | employment_status | TEXT | Yes | `PREBOARDING`, `ACTIVE`, `ON_LEAVE`, `TERMINATED` |
| Employee | hire_date | DATE | Yes | ISO date |
| Employee | start_date | DATE | Yes | On/after hire date |
| Employee | end_date | DATE | No | On/after start date |
| Role | role_id | TEXT PK | Yes | `ROLE-` + three digits |
| Role | role_name | TEXT UQ | Yes | Non-empty |
| Role | access_tier | TEXT | Yes | `STANDARD`, `ELEVATED`, `PRIVILEGED` |
| Role | is_active | INTEGER | Yes | 0 or 1 |
| Department | department_id | TEXT PK | Yes | `DEPT-` + three digits |
| Department | department_name | TEXT UQ | Yes | Non-empty |
| Department | cost_center | TEXT UQ | Yes | `CC-` + four digits |
| Manager | manager_id | TEXT PK | Yes | `MGR-` + four digits |
| Manager | employee_id | TEXT FK UQ | No | Existing Employee, nullable for synthetic manager directory |
| Manager | manager_name | TEXT | Yes | Non-empty |
| Manager | department_id | TEXT FK | Yes | Existing Department |
| OnboardingCase | onboarding_id | TEXT PK | Yes | `ONB-YYYY-` + six digits |
| OnboardingCase | employee_id | TEXT FK | Yes | Existing Employee |
| OnboardingCase | status | TEXT | Yes | `DRAFT`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, `CANCELLED` |
| OnboardingCase | opened_date | DATE | Yes | On/before start date |
| OnboardingCase | target_date | DATE | Yes | Employee start date |
| OnboardingCase | completed_date | DATE | No | On/after opened date |
| Task | task_id | TEXT PK | Yes | `TASK-<onboarding-id>-NNN` |
| Task | onboarding_id | TEXT FK | Yes | Existing OnboardingCase |
| Task | owner_team | TEXT | Yes | `HR`, `IT`, `FACILITIES`, `MANAGER` |
| Task | task_type | TEXT | Yes | `DOCUMENTS`, `ACCOUNT_SETUP`, `EQUIPMENT`, `ORIENTATION`, `ACKNOWLEDGEMENT`, `EXIT` |
| Task | status | TEXT | Yes | `PENDING`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED`, `CANCELLED` |
| Task | due_date | DATE | Yes | ISO date |
| Task | completed_date | DATE | No | On/after creation date |
| Dependency | dependency_id | TEXT PK | Yes | `DEP-` + eight digits |
| Dependency | task_id | TEXT FK | Yes | Existing Task |
| Dependency | prerequisite_task_id | TEXT FK | Yes | Existing Task; not same task |
| AccessRole | access_role_id | TEXT PK | Yes | `AR-` + four digits |
| AccessRole | role_id | TEXT FK | Yes | Existing Role |
| AccessRole | system_name | TEXT | Yes | `HRIS`, `CRM`, `ERP`, `GITHUB`, `CLOUD`, `EMAIL` |
| AccessRole | access_level | TEXT | Yes | `READ`, `WRITE`, `ADMIN` |
| AccessGrant | grant_id | TEXT PK | Yes | `GRANT-<employee-id>-NNN` |
| AccessGrant | employee_id | TEXT FK | Yes | Existing Employee |
| AccessGrant | access_role_id | TEXT FK | Yes | Existing AccessRole |
| AccessGrant | status | TEXT | Yes | `PENDING_APPROVAL`, `ACTIVE`, `REVOKED`, `EXPIRED`, `REJECTED` |
| AccessGrant | approved_by | TEXT FK | No | Existing Manager |
| AccessGrant | requested_at | TIMESTAMP | Yes | ISO-8601 |
| AccessGrant | approved_at | TIMESTAMP | No | At/after requested_at |
| AccessGrant | effective_from | DATE | Yes | ISO date |
| AccessGrant | effective_to | DATE | No | On/after effective_from |
| Asset | asset_id | TEXT PK | Yes | `AST-` + six digits |
| Asset | asset_type | TEXT | Yes | `LAPTOP`, `MONITOR`, `PHONE`, `ACCESS_CARD`, `HEADSET` |
| Asset | serial_number | TEXT UQ | Yes | Synthetic unique serial |
| Asset | asset_status | TEXT | Yes | `AVAILABLE`, `ASSIGNED`, `IN_REPAIR`, `RETIRED` |
| AssetAssignment | assignment_id | TEXT PK | Yes | `ASG-` + eight digits |
| AssetAssignment | asset_id | TEXT FK | Yes | Existing Asset |
| AssetAssignment | employee_id | TEXT FK | Yes | Existing Employee |
| AssetAssignment | status | TEXT | Yes | `ASSIGNED`, `ACKNOWLEDGED`, `RETURNED`, `LOST` |
| AssetAssignment | assigned_at | DATE | Yes | ISO date |
| AssetAssignment | acknowledged_at | DATE | No | On/after assigned date |
| AssetAssignment | returned_at | DATE | No | On/after assigned date |
| OffboardingCase | offboarding_id | TEXT PK | Yes | `OFF-YYYY-` + six digits |
| OffboardingCase | employee_id | TEXT FK | Yes | Existing Employee |
| OffboardingCase | reason | TEXT | Yes | `RESIGNATION`, `CONTRACT_END`, `TERMINATION`, `RETIREMENT` |
| OffboardingCase | status | TEXT | Yes | `OPEN`, `IN_PROGRESS`, `BLOCKED`, `COMPLETED` |
| OffboardingCase | last_working_date | DATE | Yes | On/after start date |
| OffboardingCase | opened_date | DATE | Yes | On/before last working date |
| AuditEvent | event_id | TEXT PK | Yes | `EVT-` + ten digits |
| AuditEvent | entity_type | TEXT | Yes | Entity/table name |
| AuditEvent | entity_id | TEXT | Yes | Non-empty entity identifier |
| AuditEvent | action | TEXT | Yes | `CREATED`, `STATUS_CHANGED`, `APPROVED`, `REVOKED`, `ASSIGNED`, `RETURNED`, `ANOMALY_INJECTED` |
| AuditEvent | actor | TEXT | No | `SYSTEM` or manager/employee ID |
| AuditEvent | event_time | TIMESTAMP | Yes | ISO-8601 |
| AuditEvent | details_json | TEXT | Yes | Valid JSON object |
| RoleHistory | history_id | TEXT PK | Yes | `RH-` + eight digits |
| RoleHistory | employee_id | TEXT FK | Yes | Existing Employee |
| RoleHistory | old_role_id | TEXT FK | No | Existing Role |
| RoleHistory | new_role_id | TEXT FK | Yes | Existing Role |
| RoleHistory | effective_date | DATE | Yes | ISO date |
| RoleHistory | reason | TEXT | Yes | Non-empty |
