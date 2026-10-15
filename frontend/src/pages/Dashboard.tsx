import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ShieldAlert, FolderKanban, Flame, Plus, Github, Upload } from "lucide-react";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell } from "recharts";
import { listFindingsForScan, listProjects, listScans } from "../services/api";
import { StatCard } from "../components/StatCard";
import { EmptyState } from "../components/EmptyState";
import { CardSkeleton } from "../components/Skeleton";
import { SeverityBadge } from "../components/SeverityBadge";
import { formatDate } from "../lib/utils";

const SEVERITY_COLORS: Record<string, string> = {
  Critical: "#E5484D",
  High: "#F0883E",
  Medium: "#E8B930",
  Low: "#5B8DEF",
  Informational: "#64748B",
};

export default function Dashboard() {
  const { data: projects, isLoading } = useQuery({ queryKey: ["projects"], queryFn: listProjects });

  const scanQueries = useQueries({
    queries: (projects ?? []).map((p) => ({
      queryKey: ["scans", p.id],
      queryFn: () => listScans(p.id),
      enabled: !!projects,
    })),
  });
  const allScans = scanQueries.flatMap((q) => q.data ?? []);
  const scansLoaded = projects !== undefined && scanQueries.every((q) => !q.isLoading);
  const completedScans = allScans.filter((s) => s.status === "completed");

  const findingQueries = useQueries({
    queries: completedScans.map((scan) => ({
      queryKey: ["scan-findings", scan.id],
      queryFn: () => listFindingsForScan(scan.id),
      enabled: scansLoaded,
    })),
  });
  const findingsLoaded = scansLoaded && findingQueries.every((q) => !q.isLoading);
  const allFindings = findingQueries.flatMap((q) => q.data ?? []);

  const totalScans = projects?.reduce((sum, p) => sum + p.scan_count, 0) ?? 0;
  const hasData = (projects?.length ?? 0) > 0;
  const criticalCount = allFindings.filter((f) => f.severity === "critical").length;
  const highCount = allFindings.filter((f) => f.severity === "high").length;
  const openCount = allFindings.filter((f) => f.status === "potential" || f.status === "confirmed" || f.status === "open").length;

  const severityData = [
    { name: "Critical", value: allFindings.filter((f) => f.severity === "critical").length },
    { name: "High", value: allFindings.filter((f) => f.severity === "high").length },
    { name: "Medium", value: allFindings.filter((f) => f.severity === "medium").length },
    { name: "Low", value: allFindings.filter((f) => f.severity === "low").length },
    { name: "Informational", value: allFindings.filter((f) => f.severity === "informational").length },
  ];

  const recentFindings = [...allFindings].sort((a, b) => b.created_at.localeCompare(a.created_at)).slice(0, 5);

  // Per-project health: open findings, critical count, last scan status.
  const projectHealth = (projects ?? []).map((p) => {
    const projectScans = allScans.filter((s) => s.project_id === p.id);
    const lastScan = [...projectScans].sort((a, b) => b.created_at.localeCompare(a.created_at))[0];
    const scanIds = new Set(projectScans.map((s) => s.id));
    const projectFindings = allFindings.filter((f) => scanIds.has(f.scan_id));
    const critical = projectFindings.filter((f) => f.severity === "critical").length;
    return {
      project: p,
      openFindings: projectFindings.length,
      critical,
      lastScan,
      healthy: critical === 0,
    };
  });

  if (!isLoading && !hasData) {
    return (
      <div className="max-w-xl mx-auto py-16 text-center">
        <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center mx-auto mb-5">
          <ShieldAlert className="h-6 w-6 text-primary" />
        </div>
        <h1 className="text-lg font-semibold text-ink-primary">Welcome to CodeShieldAI</h1>
        <p className="text-sm text-ink-tertiary mt-2">Analyze your first application to see its security posture here.</p>
        <div className="flex items-center justify-center gap-3 mt-6">
          <Link to="/projects" className="btn-primary flex items-center gap-1.5">
            <Plus className="h-4 w-4" /> Create your first project
          </Link>
        </div>
        <div className="flex items-center justify-center gap-6 mt-8 text-xs text-ink-tertiary">
          <span className="flex items-center gap-1.5"><Github className="h-3.5 w-3.5" /> Import a GitHub repository</span>
          <span className="flex items-center gap-1.5"><Upload className="h-3.5 w-3.5" /> or upload a ZIP</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div>
        <h1 className="text-page-title text-ink-primary">Overview</h1>
        <p className="text-sm text-ink-tertiary mt-1">Your security posture across all projects.</p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {isLoading ? (
          <>
            <CardSkeleton /><CardSkeleton /><CardSkeleton /><CardSkeleton />
          </>
        ) : (
          <>
            <StatCard label="Open findings" value={findingsLoaded ? openCount : "—"} icon={ShieldAlert} />
            <StatCard label="Critical" value={findingsLoaded ? criticalCount : "—"} icon={Flame} tone="critical" />
            <StatCard label="High" value={findingsLoaded ? highCount : "—"} icon={ShieldAlert} />
            <StatCard label="Projects / Scans" value={`${projects?.length ?? 0} / ${totalScans}`} icon={FolderKanban} />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div className="card p-5">
          <h3 className="text-section-title text-ink-primary mb-4">Findings by severity</h3>
          {!findingsLoaded ? (
            <CardSkeleton />
          ) : allFindings.length === 0 ? (
            <EmptyState icon={ShieldAlert} title="No verified findings detected" description="Run a scan to see severity breakdowns here." />
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <BarChart data={severityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E2A38" vertical={false} />
                <XAxis dataKey="name" stroke="#6B7A8A" fontSize={11} tickLine={false} axisLine={false} />
                <YAxis stroke="#6B7A8A" fontSize={12} tickLine={false} axisLine={false} allowDecimals={false} />
                <Tooltip contentStyle={{ background: "#151F29", border: "1px solid #1E2A38", borderRadius: 6 }} labelStyle={{ color: "#E7ECF2" }} />
                <Bar dataKey="value" radius={[3, 3, 0, 0]}>
                  {severityData.map((entry) => <Cell key={entry.name} fill={SEVERITY_COLORS[entry.name]} />)}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        <div className="card p-5">
          <h3 className="text-section-title text-ink-primary mb-4">Recent findings</h3>
          {!findingsLoaded ? (
            <CardSkeleton />
          ) : recentFindings.length === 0 ? (
            <EmptyState icon={ShieldAlert} title="No verified findings detected" description="Findings will appear here once analysis runs." />
          ) : (
            <div className="divide-y divide-border">
              {recentFindings.map((f) => (
                <Link key={f.id} to={`/findings/${f.id}`} className="flex items-center justify-between py-2.5 hover:bg-surface-alt/50 -mx-1 px-1 rounded transition-colors">
                  <span className="text-sm text-ink-secondary truncate">{f.title}</span>
                  <SeverityBadge severity={f.severity} />
                </Link>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="px-5 py-4 border-b border-border">
          <h3 className="text-section-title text-ink-primary">Project health</h3>
        </div>
        {isLoading ? (
          <div className="p-5"><CardSkeleton /></div>
        ) : (
          <div className="overflow-x-auto">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Project</th><th>Open</th><th>Critical</th><th>Last scan</th><th>Status</th>
                </tr>
              </thead>
              <tbody>
                {projectHealth.map(({ project, openFindings, critical, lastScan, healthy }) => (
                  <tr key={project.id}>
                    <td>
                      <Link to={`/projects/${project.id}`} className="text-ink-primary hover:text-primary">{project.name}</Link>
                    </td>
                    <td className="text-xs">{findingsLoaded ? openFindings : "—"}</td>
                    <td className="text-xs">{findingsLoaded ? critical : "—"}</td>
                    <td className="text-xs">{lastScan ? formatDate(lastScan.created_at) : "Never"}</td>
                    <td>
                      {!findingsLoaded || !lastScan ? (
                        <span className="text-xs text-ink-disabled">—</span>
                      ) : (
                        <span className={`badge ${healthy ? "bg-success/15 text-success border border-success/30" : "bg-critical/15 text-critical border border-critical/30"}`}>
                          {healthy ? "Healthy" : "Attention"}
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
