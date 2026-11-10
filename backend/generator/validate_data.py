import argparse, json, sqlite3
from pathlib import Path

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--db",required=True)
    p.add_argument("--report",default="validation_summary.json")
    a=p.parse_args()
    con=sqlite3.connect(a.db); con.row_factory=sqlite3.Row
    checks={}
    checks["foreign_key_violations"]=[dict(x) for x in con.execute("PRAGMA foreign_key_check")]
    for table,col in [("Employee","employee_id"),("Task","task_id"),("AccessGrant","grant_id"),("Asset","asset_id"),("OnboardingCase","onboarding_id")]:
        checks[f"{table.lower()}_duplicate_primary_keys"]=con.execute(f"SELECT COUNT(*)-COUNT(DISTINCT {col}) FROM {table}").fetchone()[0]
    checks["invalid_employee_dates"]=con.execute("SELECT COUNT(*) FROM Employee WHERE start_date < hire_date OR (end_date IS NOT NULL AND end_date < start_date)").fetchone()[0]
    checks["active_grants_for_terminated"]=con.execute("""SELECT COUNT(*) FROM AccessGrant g JOIN Employee e USING(employee_id)
      WHERE g.status='ACTIVE' AND e.employment_status='TERMINATED'""").fetchone()[0]
    checks["active_asset_assignment_conflicts"]=con.execute("""SELECT COUNT(*) FROM (
      SELECT asset_id FROM AssetAssignment WHERE status IN ('ASSIGNED','ACKNOWLEDGED') GROUP BY asset_id HAVING COUNT(*)>1)""").fetchone()[0]
    checks["recovered_assets_still_assigned"]=con.execute("""SELECT COUNT(*) FROM Asset a WHERE a.asset_status='ASSIGNED'
      AND EXISTS (SELECT 1 FROM AssetAssignment x WHERE x.asset_id=a.asset_id AND x.status='RETURNED')""").fetchone()[0]
    checks["task_dependency_cycle_candidates"]=con.execute("""SELECT COUNT(*) FROM Dependency d JOIN Dependency r
      ON d.task_id=r.prerequisite_task_id AND d.prerequisite_task_id=r.task_id""").fetchone()[0]
    counts={t:con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in
      ["Employee","Role","Department","Manager","OnboardingCase","Task","Dependency","AccessRole","AccessGrant","Asset","AssetAssignment","OffboardingCase","AuditEvent","RoleHistory"]}
    # Expected challenge anomalies are reported, not treated as unexplained DB corruption.
    integrity_ok=(len(checks["foreign_key_violations"])==0 and checks["employee_duplicate_primary_keys"]==0
      and checks["task_duplicate_primary_keys"]==0 and checks["accessgrant_duplicate_primary_keys"]==0
      and checks["asset_duplicate_primary_keys"]==0 and checks["onboardingcase_duplicate_primary_keys"]==0
      and checks["invalid_employee_dates"]==0)
    report={"integrity_pass":integrity_ok,"counts":counts,"checks":checks,
      "note":"Lifecycle/anomaly checks are intentionally expected to be non-zero for labelled challenge scenarios. Compare with data/ground_truth/ground_truth.csv."}
    Path(a.report).write_text(json.dumps(report,indent=2),encoding="utf-8")
    print(json.dumps(report,indent=2))
    con.close()
if __name__=="__main__": main()
