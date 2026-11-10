
import { useEffect, useState, useCallback } from "react";
import {
  LayoutDashboard, Users, ClipboardList, ShieldCheck, Laptop,
  UserMinus, AlertTriangle, Search, RefreshCw, Activity, X,
  CheckCircle, XCircle, Eye, FileText
} from "lucide-react";

import {
  ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip,
  CartesianGrid, PieChart, Pie, Cell, Legend
} from "recharts";

import "./App.css";

const API = "http://127.0.0.1:8000";

const EMPTY_DASHBOARD = {
  totals: {
    employees: 0,
    tasks: 0,
    access_grants: 0,
    assets: 0,
    onboarding_cases: 0,
    offboarding_cases: 0
  },
  employee_status: [],
  task_status: [],
  grant_status: [],
  asset_status: []
};

function getList(data, key) {
  if (Array.isArray(data)) return data;
  if (key && Array.isArray(data?.[key])) return data[key];
  if (Array.isArray(data?.items)) return data.items;
  if (Array.isArray(data?.results)) return data.results;
  if (Array.isArray(data?.data)) return data.data;
  return [];
}

async function apiRequest(path, options = {}) {
  const response = await fetch(`${API}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {})
    }
  });

  const text = await response.text();
  let result = {};

  try {
    result = text ? JSON.parse(text) : {};
  } catch {
    result = { message: text };
  }

  if (!response.ok) {
    const detail =
      typeof result.detail === "string"
        ? result.detail
        : typeof result.detail === "object"
          ? JSON.stringify(result.detail)
          : result.message || `Request failed (${response.status})`;

    throw new Error(detail);
  }

  return result;
}

// ---------------- COMMON COMPONENTS ----------------

function StatusBadge({ status }) {
  const value = String(status || "UNKNOWN").toUpperCase();

  let className = "status-badge";

  if (
    ["ACTIVE", "COMPLETED", "APPROVED", "ACKNOWLEDGED", "AVAILABLE"].includes(value)
  ) {
    className += " status-success";
  } else if (
    ["PENDING", "PENDING_APPROVAL", "IN_PROGRESS", "ON_LEAVE"].includes(value)
  ) {
    className += " status-warning";
  } else if (
    ["TERMINATED", "REVOKED", "REJECTED", "BLOCKED", "LOST", "CANCELLED"].includes(value)
  ) {
    className += " status-danger";
  } else {
    className += " status-neutral";
  }

  return (
    <span className={className}>
      {value.replaceAll("_", " ")}
    </span>
  );
}

function StatCard({ title, value, icon: Icon, description }) {
  return (
    <div className="stat-card">
      <div className="stat-card-top">
        <span>{title}</span>
        <div className="stat-icon">
          <Icon size={20} />
        </div>
      </div>
      <h2>{Number(value || 0).toLocaleString()}</h2>
      {description && <p>{description}</p>}
    </div>
  );
}

function EmptyState({ message = "No records found." }) {
  return <div className="empty-state">{message}</div>;
}

function SearchBox({ value, onChange, placeholder }) {
  return (
    <div className="search-box">
      <Search size={18} />
      <input
        value={value}
        onChange={e => onChange(e.target.value)}
        placeholder={placeholder}
      />
    </div>
  );
}

// ---------------- MAIN APP ----------------

function App() {
  const [page, setPage] = useState("Dashboard");

  const [dashboard, setDashboard] = useState(EMPTY_DASHBOARD);
  const [employees, setEmployees] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [accessGrants, setAccessGrants] = useState([]);
  const [assets, setAssets] = useState([]);
  const [offboarding, setOffboarding] = useState([]);
  const [anomalies, setAnomalies] = useState([]);
  const [auditEvents, setAuditEvents] = useState([]);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState("");
  const [successMessage, setSuccessMessage] = useState("");

  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState("ALL");

  const [selectedEmployee, setSelectedEmployee] = useState(null);
  const [updatingTaskId, setUpdatingTaskId] = useState(null);
  const [updatingGrantId, setUpdatingGrantId] = useState(null);
  const [resolvingAnomalyId, setResolvingAnomalyId] = useState(null);

  // New state for the in-app anomaly resolution window.
  const [resolutionDraft, setResolutionDraft] = useState(null);

  // ---------------- LOAD ALL DATA ----------------

  const loadData = useCallback(async (showRefresh = false) => {
    if (showRefresh) setRefreshing(true);
    else setLoading(true);

    setError("");

    const requests = [
      {
        name: "Dashboard",
        path: "/api/dashboard",
        setter: setDashboard,
        normalize: data => data
      },
      {
        name: "Employees",
        path: "/api/employees?limit=100",
        setter: setEmployees,
        normalize: data => getList(data)
      },
      {
        name: "Tasks",
        path: "/api/tasks?limit=100",
        setter: setTasks,
        normalize: data => getList(data)
      },
      {
        name: "Access grants",
        path: "/api/access-grants",
        setter: setAccessGrants,
        normalize: data => getList(data)
      },
      {
        name: "Assets",
        path: "/api/assets",
        setter: setAssets,
        normalize: data => getList(data)
      },
      {
        name: "Offboarding",
        path: "/api/offboarding",
        setter: setOffboarding,
        normalize: data => getList(data)
      },
      {
        name: "Anomalies",
        path: "/api/anomalies",
        setter: setAnomalies,
        normalize: data => getList(data, "anomalies")
      },
      {
        name: "Audit events",
        path: "/api/audit-events?limit=100",
        setter: setAuditEvents,
        normalize: data => getList(data, "events")
      }
    ];

    const results = await Promise.allSettled(
      requests.map(item => apiRequest(item.path))
    );

    const failed = [];

    results.forEach((result, index) => {
      const request = requests[index];

      if (result.status === "fulfilled") {
        try {
          request.setter(request.normalize(result.value));
        } catch (err) {
          failed.push(`${request.name}: ${err.message}`);
        }
      } else {
        failed.push(`${request.name}: ${result.reason.message}`);
      }
    });

    if (failed.length) {
      console.error("API loading errors:", failed);
      setError(failed.join(" | "));
    }

    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  function clearMessages() {
    setError("");
    setSuccessMessage("");
  }

  // ---------------- FILTERING ----------------

  const filteredEmployees = employees.filter(employee => {
    const text = search.toLowerCase();

    const matchesSearch =
      !text ||
      String(employee.full_name || "").toLowerCase().includes(text) ||
      String(employee.employee_id || "").toLowerCase().includes(text) ||
      String(employee.email || "").toLowerCase().includes(text);

    const matchesStatus =
      statusFilter === "ALL" ||
      employee.employment_status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  const filteredTasks = tasks.filter(task => {
    const text = search.toLowerCase();

    return (
      !text ||
      String(task.task_id || "").toLowerCase().includes(text) ||
      String(task.task_type || "").toLowerCase().includes(text) ||
      String(task.owner_team || "").toLowerCase().includes(text) ||
      String(task.onboarding_id || "").toLowerCase().includes(text)
    );
  });

  const filteredGrants = accessGrants.filter(grant => {
    const text = search.toLowerCase();

    const matchesSearch =
      !text ||
      String(grant.grant_id || "").toLowerCase().includes(text) ||
      String(grant.employee_id || "").toLowerCase().includes(text) ||
      String(grant.full_name || "").toLowerCase().includes(text) ||
      String(grant.system_name || "").toLowerCase().includes(text);

    const matchesStatus =
      statusFilter === "ALL" || grant.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // ---------------- TASK ACTION ----------------

  async function updateTaskStatus(taskId, newStatus) {
    setUpdatingTaskId(taskId);
    clearMessages();

    try {
      await apiRequest(`/api/tasks/${taskId}/status`, {
        method: "PATCH",
        body: JSON.stringify({
          status: newStatus,
          actor: "WORKFLOW_ADMIN"
        })
      });

      setSuccessMessage(`Task ${taskId} updated successfully.`);
      await loadData(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingTaskId(null);
    }
  }

  // ---------------- ACCESS ACTION ----------------

  async function updateAccessGrant(grantId, action) {
    setUpdatingGrantId(grantId);
    clearMessages();

    try {
      await apiRequest(`/api/access-grants/${grantId}/${action}`, {
        method: "POST",
        body: JSON.stringify({ actor: "IT_ADMIN" })
      });

      setSuccessMessage(
        `Access grant ${grantId} ${action === "approve" ? "approved" : "revoked"} successfully.`
      );

      await loadData(true);
    } catch (err) {
      setError(err.message);
    } finally {
      setUpdatingGrantId(null);
    }
  }

  // ---------------- OPEN ANOMALY RESOLUTION ----------------

  function openResolution(item) {
    clearMessages();
    setResolutionDraft(item);
  }

  // ---------------- SUBMIT ANOMALY RESOLUTION ----------------

  async function resolveAnomaly(item, reason, keepAssignmentId = "") {
    const record = item.record || {};
    const type = item.type || item.anomaly_type;

    if (!reason || !reason.trim()) {
      setError("Please enter a resolution reason.");
      return;
    }

    const payload = {
      anomaly_type: type,
      actor: "WORKFLOW_ADMIN",
      reason: reason.trim()
    };

    if (
      type === "ACTIVE_GRANT_FOR_TERMINATED" ||
      type === "ACTIVE_GRANT_WITHOUT_APPROVAL"
    ) {
      payload.grant_id = record.grant_id;
    }

    if (type === "ASSET_ASSIGNMENT_CONFLICT") {
      if (!keepAssignmentId || !keepAssignmentId.trim()) {
        setError("Please enter the assignment ID to retain.");
        return;
      }

      payload.asset_id = record.asset_id;
      payload.keep_assignment_id = keepAssignmentId.trim();
    }

    if (type === "RETURNED_ASSET_STILL_ASSIGNED") {
      payload.asset_id = record.asset_id;
    }

    if (type === "TASK_DEPENDENCY_CYCLE") {
      payload.task_id = record.task_id;
      payload.prerequisite_task_id = record.prerequisite_task_id;
    }

    const resolutionId =
      `${type}-${record.grant_id || record.asset_id || record.task_id || ""}`;

    setResolvingAnomalyId(resolutionId);
    clearMessages();

    try {
      const result = await apiRequest("/api/anomalies/resolve", {
        method: "POST",
        body: JSON.stringify(payload)
      });

      setSuccessMessage(
        result.message || `${type} resolved successfully.`
      );

      setResolutionDraft(null);
      await loadData(true);
    } catch (err) {
      setError(`Could not resolve anomaly: ${err.message}`);
    } finally {
      setResolvingAnomalyId(null);
    }
  }

  // ---------------- EMPLOYEE DETAILS ----------------

  async function viewEmployee(employeeId) {
    clearMessages();

    try {
      const result = await apiRequest(`/api/employees/${employeeId}`);
      setSelectedEmployee(result);
    } catch (err) {
      setError(err.message);
    }
  }

  function changePage(nextPage) {
    setPage(nextPage);
    setSearch("");
    setStatusFilter("ALL");
    clearMessages();
  }

  // ---------------- NAVIGATION ----------------

  const navigation = [
    { name: "Dashboard", icon: LayoutDashboard },
    { name: "Employees", icon: Users },
    { name: "Tasks", icon: ClipboardList },
    { name: "Access Management", icon: ShieldCheck },
    { name: "Assets", icon: Laptop },
    { name: "Offboarding", icon: UserMinus },
    { name: "Anomalies", icon: AlertTriangle },
    { name: "Audit Log", icon: FileText }
  ];

  const totals = dashboard?.totals || EMPTY_DASHBOARD.totals;

  // ---------------- MAIN RENDER ----------------

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-icon">
            <Activity size={23} />
          </div>
          <div>
            <h2>LifeCycleIQ</h2>
            <span>Employee Operations</span>
          </div>
        </div>

        <div className="sidebar-label">WORKSPACE</div>

        <nav className="sidebar-nav">
          {navigation.map(item => {
            const Icon = item.icon;

            return (
              <button
                key={item.name}
                className={`nav-item ${page === item.name ? "active" : ""}`}
                onClick={() => changePage(item.name)}
              >
                <Icon size={19} />
                <span>{item.name}</span>
              </button>
            );
          })}
        </nav>

        <div className="sidebar-footer">
          <div className="online-dot" />
          <span>Workflow engine connected</span>
        </div>
      </aside>

      <main className="main-content">
        <header className="topbar">
          <div>
            <h1>{page}</h1>
            <p>Employee lifecycle and workflow orchestration</p>
          </div>

          <button
            className="refresh-button"
            onClick={() => loadData(true)}
            disabled={refreshing}
          >
            <RefreshCw
              size={17}
              className={refreshing ? "spin" : ""}
            />
            {refreshing ? "Refreshing..." : "Refresh"}
          </button>
        </header>

        <div className="page-content">
          {error && (
            <div className="error-message">
              <AlertTriangle size={18} />
              <span>{error}</span>
              <button onClick={() => setError("")}>
                <X size={17} />
              </button>
            </div>
          )}

          {successMessage && (
            <div className="success-message">
              <CheckCircle size={18} />
              <span>{successMessage}</span>
              <button onClick={() => setSuccessMessage("")}>
                <X size={17} />
              </button>
            </div>
          )}

          {loading ? (
            <div className="loading-state">
              <RefreshCw className="spin" size={25} />
              <p>Loading LifeCycleIQ data...</p>
            </div>
          ) : (
            <>
              {page === "Dashboard" && (
                <DashboardPage
                  totals={totals}
                  dashboard={dashboard}
                  anomalies={anomalies}
                />
              )}

              {page === "Employees" && (
                <EmployeesPage
                  employees={filteredEmployees}
                  search={search}
                  setSearch={setSearch}
                  statusFilter={statusFilter}
                  setStatusFilter={setStatusFilter}
                  onView={viewEmployee}
                />
              )}

              {page === "Tasks" && (
                <TasksPage
                  tasks={filteredTasks}
                  search={search}
                  setSearch={setSearch}
                  onUpdate={updateTaskStatus}
                  updatingTaskId={updatingTaskId}
                />
              )}

              {page === "Access Management" && (
                <AccessPage
                  grants={filteredGrants}
                  search={search}
                  setSearch={setSearch}
                  statusFilter={statusFilter}
                  setStatusFilter={setStatusFilter}
                  onUpdate={updateAccessGrant}
                  updatingGrantId={updatingGrantId}
                />
              )}

              {page === "Assets" && (
                <AssetsPage assets={assets} />
              )}

              {page === "Offboarding" && (
                <OffboardingPage cases={offboarding} />
              )}

              {page === "Anomalies" && (
                <AnomaliesPage
                  anomalies={anomalies}
                  onResolve={openResolution}
                  resolvingAnomalyId={resolvingAnomalyId}
                />
              )}

              {page === "Audit Log" && (
                <AuditPage events={auditEvents} />
              )}
            </>
          )}
        </div>
      </main>

      {selectedEmployee && (
        <EmployeeModal
          employee={selectedEmployee}
          onClose={() => setSelectedEmployee(null)}
        />
      )}

      {resolutionDraft && (
        <ResolutionModal
          item={resolutionDraft}
          onClose={() => setResolutionDraft(null)}
          onSubmit={resolveAnomaly}
          loading={Boolean(resolvingAnomalyId)}
        />
      )}
    </div>
  );
}

// ---------------- DASHBOARD ----------------

function DashboardPage({ totals, dashboard, anomalies }) {
  const employeeData = dashboard.employee_status || [];
  const taskData = dashboard.task_status || [];
  const grantData = dashboard.grant_status || [];
  const assetData = dashboard.asset_status || [];

  return (
    <div>
      <div className="welcome-section">
        <div>
          <h2>Employee Lifecycle Overview</h2>
          <p>Monitor your workforce, tasks, access and assets.</p>
        </div>
        <div className="live-indicator">
          <span className="online-dot" /> Live data
        </div>
      </div>

      <div className="stats-grid">
        <StatCard
          title="Total Employees"
          value={totals.employees}
          icon={Users}
          description="Workforce records"
        />
        <StatCard
          title="Total Tasks"
          value={totals.tasks}
          icon={ClipboardList}
          description="Lifecycle tasks"
        />
        <StatCard
          title="Access Grants"
          value={totals.access_grants}
          icon={ShieldCheck}
          description="Employee permissions"
        />
        <StatCard
          title="Total Assets"
          value={totals.assets}
          icon={Laptop}
          description="Equipment inventory"
        />
      </div>

      <div className="charts-grid">
        <ChartPanel
          title="Employee Status"
          subtitle="Workforce distribution"
          data={employeeData}
          type="pie"
        />
        <ChartPanel
          title="Task Status"
          subtitle="Workflow progress"
          data={taskData}
        />
        <ChartPanel
          title="Access Grant Status"
          subtitle="Permission distribution"
          data={grantData}
        />
        <ChartPanel
          title="Asset Status"
          subtitle="Equipment distribution"
          data={assetData}
        />
      </div>

      <div className="panel">
        <div className="panel-heading">
          <div>
            <h3>Anomaly Monitoring</h3>
            <p>Potential lifecycle and compliance issues</p>
          </div>
          <span className="count-label">
            {anomalies.length} findings
          </span>
        </div>

        {anomalies.length === 0 ? (
          <EmptyState message="No anomalies detected." />
        ) : (
          <div className="anomaly-list">
            {anomalies.slice(0, 6).map((item, index) => (
              <AnomalyRow
                item={item}
                key={`${item.type}-${index}`}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

function ChartPanel({ title, subtitle, data, type }) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
      </div>

      {!data.length ? (
        <EmptyState />
      ) : (
        <ResponsiveContainer width="100%" height={260}>
          {type === "pie" ? (
            <PieChart>
              <Pie
                data={data}
                dataKey="count"
                nameKey="status"
                cx="50%"
                cy="50%"
                outerRadius={85}
                label
              >
                {data.map((item, index) => (
                  <Cell
                    key={`${item.status}-${index}`}
                    fill={
                      ["#665df5", "#16a879", "#f4a340", "#e15b64"][
                        index % 4
                      ]
                    }
                  />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          ) : (
            <BarChart data={data}>
              <CartesianGrid
                strokeDasharray="3 3"
                vertical={false}
              />
              <XAxis dataKey="status" />
              <YAxis />
              <Tooltip />
              <Bar
                dataKey="count"
                fill="#665df5"
                radius={[6, 6, 0, 0]}
              />
            </BarChart>
          )}
        </ResponsiveContainer>
      )}
    </div>
  );
}

// ---------------- ANOMALIES ----------------

function AnomalyRow({ item }) {
  const record = item.record || {};

  return (
    <div className="anomaly-row">
      <div className="anomaly-icon">
        <AlertTriangle size={18} />
      </div>

      <div className="anomaly-info">
        <strong>
          {item.type || item.anomaly_type || "Detected anomaly"}
        </strong>
        <span>
          {item.description || item.message || "Review this record"}
        </span>
        <small>
          {record.employee_id && `Employee: ${record.employee_id}`}
          {record.full_name && ` — ${record.full_name}`}
          {record.grant_id && ` — Grant: ${record.grant_id}`}
          {record.asset_id && ` — Asset: ${record.asset_id}`}
          {record.task_id && ` — Task: ${record.task_id}`}
        </small>
      </div>

      <span className="anomaly-severity">
        {item.severity || "REVIEW"}
      </span>
    </div>
  );
}

function AnomaliesPage({
  anomalies,
  onResolve,
  resolvingAnomalyId
}) {
  const critical = anomalies.filter(
    a => a.severity === "CRITICAL"
  ).length;

  const high = anomalies.filter(
    a => a.severity === "HIGH"
  ).length;

  const medium = anomalies.filter(
    a => a.severity === "MEDIUM"
  ).length;

  function getResolutionId(item) {
    const record = item.record || {};

    return `${
      item.type || item.anomaly_type
    }-${
      record.grant_id || record.asset_id || record.task_id || ""
    }`;
  }

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Anomaly Detection</h3>
          <p>
            Potential security, workflow and compliance issues
          </p>
        </div>
        <span className="count-label">
          {anomalies.length} findings
        </span>
      </div>

      <div className="stats-grid anomaly-stats">
        <StatCard
          title="Critical"
          value={critical}
          icon={AlertTriangle}
          description="Immediate attention"
        />
        <StatCard
          title="High"
          value={high}
          icon={AlertTriangle}
          description="High priority"
        />
        <StatCard
          title="Medium"
          value={medium}
          icon={AlertTriangle}
          description="Needs review"
        />
      </div>

      {anomalies.length === 0 ? (
        <EmptyState message="No anomalies detected." />
      ) : (
        <div className="anomaly-list">
          {anomalies.map((item, index) => {
            const resolutionId = getResolutionId(item);
            const isResolving =
              resolvingAnomalyId === resolutionId;

            return (
              <div
                className="anomaly-resolution-row"
                key={`${item.type || item.anomaly_type}-${index}`}
              >
                <div className="anomaly-resolution-info">
                  <AnomalyRow item={item} />
                </div>

                <button
                  className="action-button approve-button"
                  disabled={Boolean(resolvingAnomalyId)}
                  onClick={() => onResolve(item)}
                >
                  {isResolving ? (
                    <>
                      <RefreshCw
                        size={14}
                        className="spin"
                      />
                      Resolving...
                    </>
                  ) : (
                    <>
                      <CheckCircle size={14} />
                      Resolve
                    </>
                  )}
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

// ---------------- ANOMALY RESOLUTION MODAL ----------------

function ResolutionModal({
  item,
  onClose,
  onSubmit,
  loading
}) {
  const [reason, setReason] = useState("");
  const [keepAssignmentId, setKeepAssignmentId] = useState("");

  const record = item.record || {};
  const type = item.type || item.anomaly_type;

  const isAssetConflict =
    type === "ASSET_ASSIGNMENT_CONFLICT";

  function handleSubmit(event) {
    event.preventDefault();
    onSubmit(item, reason, keepAssignmentId);
  }

  return (
    <div
      className="employee-modal"
      onClick={loading ? undefined : onClose}
    >
      <div
        className="employee-modal-content resolution-modal"
        onClick={event => event.stopPropagation()}
      >
        <div className="modal-heading">
          <div>
            <h2>Review anomaly resolution</h2>
            <p>
              Review the affected record before taking action.
            </p>
          </div>

          <button
            className="close-button"
            onClick={onClose}
            disabled={loading}
            type="button"
          >
            <X size={20} />
          </button>
        </div>

        <div className="modal-section">
          <h3>{type}</h3>

          <div className="employee-details-grid">
            {Object.entries(record).map(([key, value]) => (
              <div key={key}>
                <span>{key.replaceAll("_", " ")}</span>
                <strong>{String(value ?? "—")}</strong>
              </div>
            ))}

            {Object.keys(record).length === 0 && (
              <p className="muted-text">
                No additional record details are available.
              </p>
            )}
          </div>
        </div>

        {isAssetConflict && (
          <div className="modal-section">
            <h3>Assignment to retain</h3>
            <p className="muted-text">
              Enter the assignment ID that should remain active.
            </p>

            <label htmlFor="keepAssignmentId">
              Assignment ID
            </label>

            <input
              id="keepAssignmentId"
              className="resolution-input"
              value={keepAssignmentId}
              onChange={event =>
                setKeepAssignmentId(event.target.value)
              }
              placeholder="Example: ASG-00000001"
              required
              disabled={loading}
            />
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <div className="modal-section">
            <h3>Resolution reason</h3>

            <label htmlFor="resolutionReason">
              Explain the corrective action
            </label>

            <textarea
              id="resolutionReason"
              className="resolution-input"
              value={reason}
              onChange={event => setReason(event.target.value)}
              placeholder="Enter the reason for resolving this anomaly..."
              rows={4}
              required
              disabled={loading}
            />
          </div>

          <div className="resolution-actions">
            <button
              type="button"
              className="view-button"
              onClick={onClose}
              disabled={loading}
            >
              Cancel
            </button>

            <button
              type="submit"
              className="action-button approve-button"
              disabled={
                loading ||
                !reason.trim() ||
                (isAssetConflict && !keepAssignmentId.trim())
              }
            >
              {loading ? (
                <>
                  <RefreshCw
                    size={14}
                    className="spin"
                  />
                  Resolving...
                </>
              ) : (
                <>
                  <CheckCircle size={14} />
                  Confirm Resolution
                </>
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

// ---------------- AUDIT LOG ----------------

function AuditPage({ events }) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Audit History</h3>
          <p>
            Track administrative actions and anomaly resolutions
          </p>
        </div>
        <span className="count-label">
          {events.length} events
        </span>
      </div>

      {!events.length ? (
        <EmptyState message="No audit events found." />
      ) : (
        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th>Event ID</th>
                <th>Action</th>
                <th>Entity Type</th>
                <th>Entity ID</th>
                <th>Actor</th>
                <th>Date & Time</th>
                <th>Details</th>
              </tr>
            </thead>

            <tbody>
              {events.map(event => (
                <tr key={event.event_id}>
                  <td>{event.event_id}</td>
                  <td>
                    <strong>{event.action}</strong>
                  </td>
                  <td>{event.entity_type}</td>
                  <td>{event.entity_id}</td>
                  <td>{event.actor}</td>
                  <td>
                    {event.event_time
                      ? new Date(event.event_time).toLocaleString()
                      : "—"}
                  </td>
                  <td>
                    {event.details?.reason ||
                      event.details_json ||
                      "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

// ---------------- EMPLOYEES ----------------

function EmployeesPage({
  employees,
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
  onView
}) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Employee Directory</h3>
          <p>Search and review employee records</p>
        </div>
        <span className="count-label">
          {employees.length} employees
        </span>
      </div>

      <div className="employee-controls">
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search name, employee ID or email..."
        />

        <select
          className="status-filter"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="ALL">All statuses</option>
          <option value="ACTIVE">Active</option>
          <option value="PREBOARDING">Preboarding</option>
          <option value="ON_LEAVE">On leave</option>
          <option value="TERMINATED">Terminated</option>
        </select>
      </div>

      <p className="employee-count">
        Showing {employees.length} employee records
      </p>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Employee</th>
              <th>Employee ID</th>
              <th>Department</th>
              <th>Role</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {employees.map(employee => (
              <tr key={employee.employee_id}>
                <td>
                  <strong>{employee.full_name}</strong>
                  <small>{employee.email}</small>
                </td>
                <td>{employee.employee_id}</td>
                <td>
                  {employee.department_name ||
                    employee.department_id}
                </td>
                <td>
                  {employee.role_name || employee.role_id}
                </td>
                <td>
                  <StatusBadge
                    status={employee.employment_status}
                  />
                </td>
                <td>
                  <button
                    className="view-button"
                    onClick={() =>
                      onView(employee.employee_id)
                    }
                  >
                    <Eye size={15} /> View
                  </button>
                </td>
              </tr>
            ))}

            {!employees.length && (
              <tr>
                <td colSpan="6">
                  <EmptyState message="No matching employees found." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------- TASKS ----------------

function TasksPage({
  tasks,
  search,
  setSearch,
  onUpdate,
  updatingTaskId
}) {
  const statuses = [
    "PENDING",
    "IN_PROGRESS",
    "BLOCKED",
    "COMPLETED",
    "CANCELLED"
  ];

  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Lifecycle Tasks</h3>
          <p>Manage employee onboarding tasks</p>
        </div>
        <span className="count-label">
          {tasks.length} tasks
        </span>
      </div>

      <SearchBox
        value={search}
        onChange={setSearch}
        placeholder="Search task ID, type or owner team..."
      />

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Task ID</th>
              <th>Task Type</th>
              <th>Owner Team</th>
              <th>Due Date</th>
              <th>Status</th>
              <th>Update Status</th>
            </tr>
          </thead>

          <tbody>
            {tasks.map(task => (
              <tr key={task.task_id}>
                <td>{task.task_id}</td>
                <td>{task.task_type}</td>
                <td>{task.owner_team}</td>
                <td>{task.due_date || "—"}</td>
                <td>
                  <StatusBadge status={task.status} />
                </td>
                <td>
                  <select
                    className="task-status-select"
                    value={task.status}
                    disabled={
                      updatingTaskId === task.task_id
                    }
                    onChange={e =>
                      onUpdate(task.task_id, e.target.value)
                    }
                  >
                    {statuses.map(status => (
                      <option key={status} value={status}>
                        {status.replaceAll("_", " ")}
                      </option>
                    ))}
                  </select>

                  {updatingTaskId === task.task_id && (
                    <span className="updating-label">
                      Updating...
                    </span>
                  )}
                </td>
              </tr>
            ))}

            {!tasks.length && (
              <tr>
                <td colSpan="6">
                  <EmptyState message="No matching tasks found." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------- ACCESS MANAGEMENT ----------------

function AccessPage({
  grants,
  search,
  setSearch,
  statusFilter,
  setStatusFilter,
  onUpdate,
  updatingGrantId
}) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Employee Access Management</h3>
          <p>
            Review, approve and revoke system permissions
          </p>
        </div>
        <span className="count-label">
          {grants.length} access grants
        </span>
      </div>

      <div className="employee-controls">
        <SearchBox
          value={search}
          onChange={setSearch}
          placeholder="Search employee, grant ID or system..."
        />

        <select
          className="status-filter"
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
        >
          <option value="ALL">All statuses</option>
          <option value="PENDING_APPROVAL">
            Pending approval
          </option>
          <option value="ACTIVE">Active</option>
          <option value="REVOKED">Revoked</option>
          <option value="EXPIRED">Expired</option>
          <option value="REJECTED">Rejected</option>
        </select>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Grant ID</th>
              <th>Employee</th>
              <th>System</th>
              <th>Access Level</th>
              <th>Requested At</th>
              <th>Status</th>
              <th>Action</th>
            </tr>
          </thead>

          <tbody>
            {grants.map(grant => (
              <tr key={grant.grant_id}>
                <td>{grant.grant_id}</td>
                <td>
                  <strong>
                    {grant.full_name || "Employee"}
                  </strong>
                  <small>{grant.employee_id}</small>
                </td>
                <td>{grant.system_name || "—"}</td>
                <td>{grant.access_level || "—"}</td>
                <td>{grant.requested_at || "—"}</td>
                <td>
                  <StatusBadge status={grant.status} />
                </td>
                <td>
                  {grant.status === "PENDING_APPROVAL" && (
                    <button
                      className="action-button approve-button"
                      disabled={
                        updatingGrantId === grant.grant_id
                      }
                      onClick={() =>
                        onUpdate(grant.grant_id, "approve")
                      }
                    >
                      <CheckCircle size={14} /> Approve
                    </button>
                  )}

                  {grant.status === "ACTIVE" && (
                    <button
                      className="action-button revoke-button"
                      disabled={
                        updatingGrantId === grant.grant_id
                      }
                      onClick={() =>
                        onUpdate(grant.grant_id, "revoke")
                      }
                    >
                      <XCircle size={14} /> Revoke
                    </button>
                  )}

                  {!["ACTIVE", "PENDING_APPROVAL"].includes(
                    grant.status
                  ) && (
                    <span className="muted-text">
                      No action
                    </span>
                  )}
                </td>
              </tr>
            ))}

            {!grants.length && (
              <tr>
                <td colSpan="7">
                  <EmptyState message="No matching access grants found." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------- ASSETS ----------------

function AssetsPage({ assets }) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Asset Management</h3>
          <p>Track company equipment and availability</p>
        </div>
        <span className="count-label">
          {assets.length} assets
        </span>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Asset ID</th>
              <th>Asset Type</th>
              <th>Serial Number</th>
              <th>Status</th>
              <th>Assigned Employee</th>
            </tr>
          </thead>

          <tbody>
            {assets.map(asset => (
              <tr key={asset.asset_id}>
                <td>{asset.asset_id}</td>
                <td>{asset.asset_type}</td>
                <td>{asset.serial_number || "—"}</td>
                <td>
                  <StatusBadge status={asset.asset_status} />
                </td>
                <td>{asset.assigned_employee || "—"}</td>
              </tr>
            ))}

            {!assets.length && (
              <tr>
                <td colSpan="5">
                  <EmptyState message="No assets found." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------- OFFBOARDING ----------------

function OffboardingPage({ cases }) {
  return (
    <div className="panel">
      <div className="panel-heading">
        <div>
          <h3>Employee Offboarding</h3>
          <p>Track employee exits and clearance cases</p>
        </div>
        <span className="count-label">
          {cases.length} cases
        </span>
      </div>

      <div className="table-wrapper">
        <table>
          <thead>
            <tr>
              <th>Case ID</th>
              <th>Employee ID</th>
              <th>Employee</th>
              <th>Reason</th>
              <th>Last Working Date</th>
              <th>Status</th>
            </tr>
          </thead>

          <tbody>
            {cases.map(item => (
              <tr key={item.offboarding_id}>
                <td>{item.offboarding_id}</td>
                <td>{item.employee_id}</td>
                <td>{item.full_name || "—"}</td>
                <td>{item.reason || "—"}</td>
                <td>{item.last_working_date || "—"}</td>
                <td>
                  <StatusBadge status={item.status} />
                </td>
              </tr>
            ))}

            {!cases.length && (
              <tr>
                <td colSpan="6">
                  <EmptyState message="No offboarding cases found." />
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

// ---------------- EMPLOYEE DETAILS MODAL ----------------

function EmployeeModal({ employee, onClose }) {
  const details =
    employee.employee || employee.data || employee;

  const employeeInfo = details.employee || details;
  const taskList = getList(details.tasks || employee.tasks);
  const grantList = getList(
    details.access_grants || employee.access_grants
  );

  return (
    <div className="employee-modal" onClick={onClose}>
      <div
        className="employee-modal-content"
        onClick={e => e.stopPropagation()}
      >
        <div className="modal-heading">
          <div>
            <h2>
              {employeeInfo.full_name || "Employee Details"}
            </h2>
            <p>{employeeInfo.employee_id}</p>
          </div>
          <button
            className="close-button"
            onClick={onClose}
          >
            <X size={20} />
          </button>
        </div>

        <div className="employee-details-grid">
          <div>
            <span>Email</span>
            <strong>{employeeInfo.email || "—"}</strong>
          </div>
          <div>
            <span>Department</span>
            <strong>
              {employeeInfo.department_name ||
                employeeInfo.department_id ||
                "—"}
            </strong>
          </div>
          <div>
            <span>Role</span>
            <strong>
              {employeeInfo.role_name ||
                employeeInfo.role_id ||
                "—"}
            </strong>
          </div>
          <div>
            <span>Employment Status</span>
            <StatusBadge
              status={employeeInfo.employment_status}
            />
          </div>
          <div>
            <span>Employment Type</span>
            <strong>
              {employeeInfo.employment_type || "—"}
            </strong>
          </div>
          <div>
            <span>Hire Date</span>
            <strong>{employeeInfo.hire_date || "—"}</strong>
          </div>
          <div>
            <span>Start Date</span>
            <strong>{employeeInfo.start_date || "—"}</strong>
          </div>
          <div>
            <span>End Date</span>
            <strong>{employeeInfo.end_date || "—"}</strong>
          </div>
        </div>

        <div className="modal-section">
          <h3>Onboarding Tasks ({taskList.length})</h3>
          {taskList.length === 0 ? (
            <p className="muted-text">
              No task details available.
            </p>
          ) : (
            taskList.map(task => (
              <div
                className="modal-list-row"
                key={task.task_id}
              >
                <span>
                  {task.task_type || task.task_id}
                </span>
                <StatusBadge status={task.status} />
              </div>
            ))
          )}
        </div>

        <div className="modal-section">
          <h3>Access Grants ({grantList.length})</h3>
          {grantList.length === 0 ? (
            <p className="muted-text">
              No access grants available.
            </p>
          ) : (
            grantList.map(grant => (
              <div
                className="modal-list-row"
                key={grant.grant_id}
              >
                <span>
                  {grant.system_name || grant.grant_id}
                </span>
                <StatusBadge status={grant.status} />
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

export default App;
