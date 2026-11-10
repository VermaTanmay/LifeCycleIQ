PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS Department (
  department_id TEXT PRIMARY KEY,
  department_name TEXT NOT NULL UNIQUE,
  cost_center TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS Role (
  role_id TEXT PRIMARY KEY,
  role_name TEXT NOT NULL UNIQUE,
  access_tier TEXT NOT NULL CHECK(access_tier IN ('STANDARD','ELEVATED','PRIVILEGED')),
  is_active INTEGER NOT NULL CHECK(is_active IN (0,1))
);

CREATE TABLE IF NOT EXISTS Manager (
  manager_id TEXT PRIMARY KEY,
  employee_id TEXT UNIQUE,
  manager_name TEXT NOT NULL,
  department_id TEXT NOT NULL REFERENCES Department(department_id),
  FOREIGN KEY(employee_id) REFERENCES Employee(employee_id)
);

CREATE TABLE IF NOT EXISTS Employee (
  employee_id TEXT PRIMARY KEY,
  full_name TEXT NOT NULL,
  email TEXT NOT NULL UNIQUE,
  department_id TEXT NOT NULL REFERENCES Department(department_id),
  role_id TEXT NOT NULL REFERENCES Role(role_id),
  manager_id TEXT,
  employment_type TEXT NOT NULL CHECK(employment_type IN ('FULL_TIME','CONTRACTOR','INTERN')),
  employment_status TEXT NOT NULL CHECK(employment_status IN ('PREBOARDING','ACTIVE','ON_LEAVE','TERMINATED')),
  hire_date TEXT NOT NULL,
  start_date TEXT NOT NULL,
  end_date TEXT,
  FOREIGN KEY(manager_id) REFERENCES Manager(manager_id),
  CHECK(start_date >= hire_date),
  CHECK(end_date IS NULL OR end_date >= start_date)
);

CREATE TABLE IF NOT EXISTS OnboardingCase (
  onboarding_id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES Employee(employee_id),
  status TEXT NOT NULL CHECK(status IN ('DRAFT','IN_PROGRESS','BLOCKED','COMPLETED','CANCELLED')),
  opened_date TEXT NOT NULL,
  target_date TEXT NOT NULL,
  completed_date TEXT,
  CHECK(target_date >= opened_date)
);

CREATE TABLE IF NOT EXISTS Task (
  task_id TEXT PRIMARY KEY,
  onboarding_id TEXT NOT NULL REFERENCES OnboardingCase(onboarding_id),
  owner_team TEXT NOT NULL CHECK(owner_team IN ('HR','IT','FACILITIES','MANAGER')),
  task_type TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('PENDING','IN_PROGRESS','BLOCKED','COMPLETED','CANCELLED')),
  due_date TEXT NOT NULL,
  completed_date TEXT
);

CREATE TABLE IF NOT EXISTS Dependency (
  dependency_id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL REFERENCES Task(task_id),
  prerequisite_task_id TEXT NOT NULL REFERENCES Task(task_id),
  UNIQUE(task_id, prerequisite_task_id),
  CHECK(task_id <> prerequisite_task_id)
);

CREATE TABLE IF NOT EXISTS AccessRole (
  access_role_id TEXT PRIMARY KEY,
  role_id TEXT NOT NULL REFERENCES Role(role_id),
  system_name TEXT NOT NULL,
  access_level TEXT NOT NULL CHECK(access_level IN ('READ','WRITE','ADMIN')),
  UNIQUE(role_id, system_name, access_level)
);

CREATE TABLE IF NOT EXISTS AccessGrant (
  grant_id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES Employee(employee_id),
  access_role_id TEXT NOT NULL REFERENCES AccessRole(access_role_id),
  status TEXT NOT NULL CHECK(status IN ('PENDING_APPROVAL','ACTIVE','REVOKED','EXPIRED','REJECTED')),
  approved_by TEXT,
  requested_at TEXT NOT NULL,
  approved_at TEXT,
  effective_from TEXT NOT NULL,
  effective_to TEXT,
  FOREIGN KEY(approved_by) REFERENCES Manager(manager_id),
  CHECK(effective_to IS NULL OR effective_to >= effective_from)
);

CREATE TABLE IF NOT EXISTS Asset (
  asset_id TEXT PRIMARY KEY,
  asset_type TEXT NOT NULL,
  serial_number TEXT NOT NULL UNIQUE,
  asset_status TEXT NOT NULL CHECK(asset_status IN ('AVAILABLE','ASSIGNED','IN_REPAIR','RETIRED'))
);

CREATE TABLE IF NOT EXISTS AssetAssignment (
  assignment_id TEXT PRIMARY KEY,
  asset_id TEXT NOT NULL REFERENCES Asset(asset_id),
  employee_id TEXT NOT NULL REFERENCES Employee(employee_id),
  status TEXT NOT NULL CHECK(status IN ('ASSIGNED','ACKNOWLEDGED','RETURNED','LOST')),
  assigned_at TEXT NOT NULL,
  acknowledged_at TEXT,
  returned_at TEXT
);

CREATE TABLE IF NOT EXISTS OffboardingCase (
  offboarding_id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES Employee(employee_id),
  reason TEXT NOT NULL,
  status TEXT NOT NULL CHECK(status IN ('OPEN','IN_PROGRESS','BLOCKED','COMPLETED')),
  last_working_date TEXT NOT NULL,
  opened_date TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS AuditEvent (
  event_id TEXT PRIMARY KEY,
  entity_type TEXT NOT NULL,
  entity_id TEXT NOT NULL,
  action TEXT NOT NULL,
  actor TEXT,
  event_time TEXT NOT NULL,
  details_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS RoleHistory (
  history_id TEXT PRIMARY KEY,
  employee_id TEXT NOT NULL REFERENCES Employee(employee_id),
  old_role_id TEXT REFERENCES Role(role_id),
  new_role_id TEXT NOT NULL REFERENCES Role(role_id),
  effective_date TEXT NOT NULL,
  reason TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_employee_status ON Employee(employment_status);
CREATE INDEX IF NOT EXISTS idx_task_status ON Task(status);
CREATE INDEX IF NOT EXISTS idx_grant_employee_status ON AccessGrant(employee_id, status);
CREATE INDEX IF NOT EXISTS idx_assignment_asset_status ON AssetAssignment(asset_id, status);
CREATE INDEX IF NOT EXISTS idx_audit_entity ON AuditEvent(entity_type, entity_id);
