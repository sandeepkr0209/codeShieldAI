import {
  useQueries,
  useQuery,
  useMutation,
  useQueryClient,
} from "@tanstack/react-query";
import { Link } from "react-router-dom";
import {
  FileText,
  Download,
  Trash2,
} from "lucide-react";

import {
  downloadReportUrl,
  generateReport,
  deleteReport,
  deleteScan,
  listProjects,
  listScans,
  listReportsForScan,
} from "../services/api";

import { EmptyState } from "../components/EmptyState";
import { CardSkeleton } from "../components/Skeleton";
import { useToast } from "../hooks/useToast";
import { formatDate } from "../lib/utils";

export default function Reports() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();

  // --------------------------------------------------
  // Projects
  // --------------------------------------------------

  const { data: projects } = useQuery({
    queryKey: ["projects"],
    queryFn: listProjects,
  });

  // --------------------------------------------------
  // Scans
  // --------------------------------------------------

  const scanQueries = useQueries({
    queries: (projects ?? []).map((p) => ({
      queryKey: ["scans", p.id],
      queryFn: () => listScans(p.id),
      enabled: !!projects,
    })),
  });

  const allScans = scanQueries.flatMap(
    (q) => q.data ?? []
  );

  const scansLoaded =
    projects !== undefined &&
    scanQueries.every((q) => !q.isLoading);

  const completedScans = allScans.filter(
    (s) => s.status === "completed"
  );

  // --------------------------------------------------
  // Reports
  // --------------------------------------------------

  const reportQueries = useQueries({
    queries: allScans.map((scan) => ({
      queryKey: ["reports", scan.id],
      queryFn: () => listReportsForScan(scan.id),
      enabled: scansLoaded,
      retry: false,
    })),
  });

  const isLoading =
    !scansLoaded ||
    reportQueries.some((q) => q.isLoading);

  const allReports = reportQueries.flatMap(
    (q) => q.data ?? []
  );

  const scansWithReports = completedScans;

  // --------------------------------------------------
  // Generate report
  // --------------------------------------------------

  const generateMutation = useMutation({
    mutationFn: (scanId: string) =>
      generateReport(scanId),

    onSuccess: (_, scanId) => {
      queryClient.invalidateQueries({
        queryKey: ["reports", scanId],
      });

      showToast(
        "Report generated",
        "success"
      );
    },

    onError: (err: Error) =>
      showToast(
        err.message,
        "error"
      ),
  });

  // --------------------------------------------------
  // Delete generated report
  // --------------------------------------------------

  const deleteReportMutation = useMutation({
    mutationFn: (reportId: string) =>
      deleteReport(reportId),

    onSuccess: (_, reportId) => {
      const report = allReports.find(
        (r) => r.id === reportId
      );

      if (report) {
        queryClient.invalidateQueries({
          queryKey: ["reports", report.scan_id],
        });
      }

      showToast(
        "Report deleted",
        "success"
      );
    },

    onError: (err: Error) =>
      showToast(
        err.message,
        "error"
      ),
  });

  // --------------------------------------------------
  // Delete scan
  // --------------------------------------------------

  const deleteScanMutation = useMutation({
    mutationFn: (scanId: string) =>
      deleteScan(scanId),

    // ------------------------------------------------
    // Optimistically remove scan from React Query
    // cache BEFORE the backend deletion completes.
    // ------------------------------------------------
    onMutate: async (scanId) => {
      // Stop any currently running scan-list requests.
      await queryClient.cancelQueries({
        queryKey: ["scans"],
      });

      // Remove the scan immediately from every
      // project-specific scan cache.
      queryClient.setQueriesData(
        {
          queryKey: ["scans"],
        },
        (oldData: unknown) => {
          if (!Array.isArray(oldData)) {
            return oldData;
          }

          return oldData.filter(
            (scan: { id: string }) =>
              scan.id !== scanId
          );
        }
      );

      // Remove the report query immediately.
      queryClient.removeQueries({
        queryKey: ["reports", scanId],
      });

      return { scanId };
    },

    // ------------------------------------------------
    // Backend deletion succeeded.
    // ------------------------------------------------
    onSuccess: (_, scanId) => {
      // Refresh scan lists to make sure the frontend
      // matches the actual backend state.
      queryClient.invalidateQueries({
        queryKey: ["scans"],
      });

      // Make absolutely sure no report query for the
      // deleted scan remains in the cache.
      queryClient.removeQueries({
        queryKey: ["reports", scanId],
      });

      showToast(
        "Scan deleted",
        "success"
      );
    },

    // ------------------------------------------------
    // Backend deletion failed.
    // ------------------------------------------------
    onError: (err: Error) => {
      // Re-fetch the scans so the optimistically removed
      // scan comes back if the deletion failed.
      queryClient.invalidateQueries({
        queryKey: ["scans"],
      });

      showToast(
        err.message,
        "error"
      );
    },
  });

  // --------------------------------------------------
  // UI
  // --------------------------------------------------

  return (
    <div className="space-y-6">

      {/* Page header */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">
          Reports
        </h1>

        <p className="text-sm text-slate-500 mt-1">
          Generated HTML security reports for completed scans.
        </p>
      </div>

      {/* ------------------------------------------------
          Completed scans
      ------------------------------------------------- */}

      {!isLoading &&
        scansWithReports.length > 0 && (
          <div className="card p-5">

            <h3 className="text-sm font-medium text-slate-300 mb-3">
              Completed scans
            </h3>

            <div className="divide-y divide-border">

              {scansWithReports.map((scan) => (
                <div
                  key={scan.id}
                  className="flex items-center justify-between py-2.5"
                >

                  {/* Scan */}
                  <Link
                    to={`/scans/${scan.id}`}
                    className="text-sm text-slate-300 hover:text-primary font-mono"
                  >
                    {scan.id.slice(0, 8)}… —{" "}
                    {scan.scan_type}
                  </Link>

                  <div className="flex items-center gap-3">

                    {/* Generate report */}
                    <button
                      onClick={() =>
                        generateMutation.mutate(
                          scan.id
                        )
                      }
                      disabled={
                        generateMutation.isPending ||
                        deleteScanMutation.isPending
                      }
                      className="px-3 py-1.5 text-xs rounded-lg bg-primary hover:bg-primary-hover text-white transition-colors disabled:opacity-60"
                    >
                      Generate
                    </button>

                    {/* Delete scan */}
                    <button
                      onClick={() => {
                        const confirmed =
                          window.confirm(
                            "Delete this scan? This will permanently delete the scan, its findings, observations, application map data, and generated reports."
                          );

                        if (confirmed) {
                          deleteScanMutation.mutate(
                            scan.id
                          );
                        }
                      }}
                      disabled={
                        deleteScanMutation.isPending
                      }
                      className="text-slate-500 hover:text-red-400 disabled:opacity-50"
                      title="Delete scan"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>

                  </div>
                </div>
              ))}

            </div>
          </div>
        )}

      {/* ------------------------------------------------
          Generated reports
      ------------------------------------------------- */}

      <div className="card p-5">

        {isLoading ? (
          <CardSkeleton />

        ) : allReports.length === 0 ? (
          <EmptyState
            icon={FileText}
            title="No reports generated yet"
            description="Generate a report from a completed scan's page, or use the list above."
          />

        ) : (
          <div className="divide-y divide-border">

            {allReports.map((r) => {
              const scan = allScans.find(
                (s) => s.id === r.scan_id
              );

              const reportTitle =
                r.report_name ||
                (scan?.scan_type === "source_code"
                  ? "Source Code Security Report"
                  : scan?.scan_type === "web_application"
                    ? "Web Application Security Report"
                    : "Security Assessment Report");

              return (
                <div
                  key={r.id}
                  className="flex items-center justify-between py-3"
                >

                  {/* Report information */}
                  <div className="flex items-center gap-3">

                    <FileText className="h-4 w-4 text-slate-500" />

                    <div>

                      <Link
                        to={`/scans/${r.scan_id}`}
                        className="text-sm text-slate-200 hover:text-primary"
                      >
                        {reportTitle}
                      </Link>

                      <p className="text-xs text-slate-500 mt-0.5">
                        Scan:{" "}
                        {r.scan_id.slice(0, 8)}
                        … ·{" "}
                        {formatDate(
                          r.created_at
                        )}
                      </p>

                    </div>
                  </div>

                  {/* Report actions */}
                  <div className="flex items-center gap-3">

                    {/* Download report */}
                    <a
                      href={downloadReportUrl(r.id)}
                      target="_blank"
                      rel="noreferrer"
                      className="text-slate-500 hover:text-primary"
                      title="Download report"
                    >
                      <Download className="h-4 w-4" />
                    </a>

                    {/* Delete report */}
                    <button
                      onClick={() => {
                        const confirmed =
                          window.confirm(
                            `Delete "${reportTitle}"? This will permanently delete the generated report.`
                          );

                        if (confirmed) {
                          deleteReportMutation.mutate(
                            r.id
                          );
                        }
                      }}
                      disabled={
                        deleteReportMutation.isPending
                      }
                      className="text-slate-500 hover:text-red-400 disabled:opacity-50"
                      title="Delete report"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>

                  </div>
                </div>
              );
            })}

          </div>
        )}

      </div>
    </div>
  );
}