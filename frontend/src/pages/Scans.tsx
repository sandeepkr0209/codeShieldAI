import { useQueries, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { ScanLine } from "lucide-react";
import { listProjects, listScans } from "../services/api";
import { EmptyState } from "../components/EmptyState";
import { CardSkeleton } from "../components/Skeleton";
import { StatusBadge } from "../components/StatusBadge";
import { formatDate } from "../lib/utils";

/**
 * Aggregates scans across every project client-side, since Phase 1's
 * API surfaces scans per-project (see API_v1 spec) rather than via a
 * single global endpoint.
 */
export default function Scans() {
  const { data: projects, isLoading: projectsLoading } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  const scanQueries = useQueries({
    queries: (projects ?? []).map((p) => ({
      queryKey: ["scans", p.id],
      queryFn: () => listScans(p.id),
      enabled: !!projects,
    })),
  });

  const isLoading = projectsLoading || scanQueries.some((q) => q.isLoading);
  const projectById = new Map(
    (projects ?? []).map((project) => [project.id, project])
  );
  const allScans = scanQueries.flatMap((q) => q.data ?? []).sort((a, b) => b.created_at.localeCompare(a.created_at));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-semibold text-slate-100">Scans</h1>
        <p className="text-sm text-slate-500 mt-1">Every scan record across all projects.</p>
      </div>

      <div className="card p-5">
        {isLoading ? (
          <div className="space-y-3">
            <CardSkeleton />
            <CardSkeleton />
          </div>
        ) : allScans.length === 0 ? (
          <EmptyState
            icon={ScanLine}
            title="No scans yet"
            description="Create a project and start a scan to see it listed here."
          />
        ) : (
          <div className="divide-y divide-border">
            {allScans.map((scan) => (
              <Link
                key={scan.id}
                to={`/scans/${scan.id}`}
                className="flex items-center justify-between py-3 hover:bg-surface-alt/50 -mx-5 px-5 transition-colors"
              >
                <div className="flex items-center gap-3 min-w-0">
                  <ScanLine className="h-4 w-4 text-slate-500 shrink-0" />
                  <div className="min-w-0">
                    <p className="text-sm text-slate-200 truncate">
                      {projectById.get(scan.project_id)?.name ?? "Unknown project"}
                      <span className="text-slate-500 font-normal">
                        {" · "}
                        {scan.scan_type === "source_code" ? "Source Code" : "Web Application"}
                      </span>
                    </p>
                    <p className="text-xs text-slate-500 mt-0.5">{formatDate(scan.created_at)}</p>
                  </div>
                </div>
                <div className="flex items-center gap-4 shrink-0">
                  <span className="text-xs text-slate-500">{scan.finding_count} findings</span>
                  <StatusBadge status={scan.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
