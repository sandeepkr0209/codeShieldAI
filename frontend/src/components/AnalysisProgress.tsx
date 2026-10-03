import { Check, Loader2, X } from "lucide-react";
import { cn } from "../lib/utils";
import type { ScanStage, ScanStatus, ScanType } from "../types";

const SOURCE_STAGES: { key: ScanStage; label: string }[] = [
  { key: "queued", label: "Uploading" },
  { key: "extracting", label: "Extracting" },
  { key: "parsing", label: "Parsing" },
  { key: "static_analysis", label: "Static Analysis" },
  { key: "ai_analysis", label: "AI Analysis" },
  { key: "completed", label: "Completed" },
];

const WEB_STAGES: { key: ScanStage; label: string }[] = [
  { key: "scope_validation", label: "Scope Validation" },
  { key: "reconnaissance", label: "Reconnaissance" },
  { key: "application_mapping", label: "App Mapping" },
  { key: "security_testing", label: "Security Testing" },
  { key: "evidence_collection", label: "Evidence" },
  { key: "verification", label: "Verification" },
  { key: "completed", label: "Completed" },
];

interface AnalysisProgressProps {
  status: ScanStatus;
  scanType: ScanType;
  currentStage: string | null;
  errorMessage?: string | null;
  warnings?: string | null;
  pagesDiscovered?: number;
  endpointsDiscovered?: number;
  requestsMade?: number;
}

export function AnalysisProgress({
  status,
  scanType,
  currentStage,
  errorMessage,
  warnings,
  pagesDiscovered,
  endpointsDiscovered,
  requestsMade,
}: AnalysisProgressProps) {
  const stages = scanType === "web_application" ? WEB_STAGES : SOURCE_STAGES;
  const failed = status === "failed";
  const currentIndex = stages.findIndex((s) => s.key === currentStage);
  const effectiveIndex = status === "completed" ? stages.length - 1 : currentIndex;

  return (
    <div className="card p-5">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-medium text-slate-300">Analysis progress</h3>
        {status === "completed" && (
          <span className={cn("text-xs font-medium", warnings ? "text-medium" : "text-success")}>
            {warnings ? "Completed with limited analysis" : "Completed successfully"}
          </span>
        )}
      </div>

      <div className="flex items-center flex-wrap gap-y-3">
        {stages.map((stage, idx) => {
          const isDone = !failed && (effectiveIndex > idx || status === "completed");
          const isCurrent = !failed && effectiveIndex === idx && status === "running";
          const isFailedHere = failed && effectiveIndex === idx;

          return (
            <div key={stage.key} className="flex items-center">
              <div className="flex flex-col items-center gap-1.5">
                <div
                  className={cn(
                    "h-7 w-7 rounded-full flex items-center justify-center border text-xs font-medium",
                    isDone && "bg-success/15 border-success/40 text-success",
                    isCurrent && "bg-primary/15 border-primary/40 text-primary",
                    isFailedHere && "bg-critical/15 border-critical/40 text-critical",
                    !isDone && !isCurrent && !isFailedHere && "bg-surface-alt border-border text-slate-500"
                  )}
                >
                  {isDone ? (
                    <Check className="h-3.5 w-3.5" />
                  ) : isCurrent ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : isFailedHere ? (
                    <X className="h-3.5 w-3.5" />
                  ) : (
                    idx + 1
                  )}
                </div>
                <span className={cn("text-[11px] whitespace-nowrap", isCurrent ? "text-slate-200" : "text-slate-500")}>
                  {stage.label}
                </span>
              </div>
              {idx < stages.length - 1 && (
                <div className={cn("w-8 sm:w-12 h-px mx-1 mb-4", isDone ? "bg-success/40" : "bg-border")} />
              )}
            </div>
          );
        })}
      </div>

      {scanType === "web_application" && (pagesDiscovered !== undefined) && (
        <div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-border">
          <div>
            <p className="text-xs text-slate-500">Pages discovered</p>
            <p className="text-sm text-slate-200 font-medium">{pagesDiscovered}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Endpoints discovered</p>
            <p className="text-sm text-slate-200 font-medium">{endpointsDiscovered}</p>
          </div>
          <div>
            <p className="text-xs text-slate-500">Requests made</p>
            <p className="text-sm text-slate-200 font-medium">{requestsMade}</p>
          </div>
        </div>
      )}

      {warnings && (
        <p className="text-xs text-medium mt-4 pt-4 border-t border-border">
          <span className="font-medium">Warnings:</span> {warnings}
        </p>
      )}
      {failed && errorMessage && (
        <p className="text-xs text-critical mt-4 pt-4 border-t border-border">{errorMessage}</p>
      )}
    </div>
  );
}
