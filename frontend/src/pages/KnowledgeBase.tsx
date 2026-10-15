
import { useQuery } from "@tanstack/react-query";
import { BookOpen, Database, Layers } from "lucide-react";

import { getKnowledgeStats } from "../services/api";
import { StatCard } from "../components/StatCard";
import { EmptyState } from "../components/EmptyState";
import { CardSkeleton } from "../components/Skeleton";

const PLANNED_SOURCES = [
  "OWASP Top 10",
  "OWASP API Security Top 10",
  "CWE",
  "CAPEC",
  "Secure Coding Guidance",
];

export default function KnowledgeBase() {
  const {
    data: stats,
    isLoading,
    isError,
  } = useQuery({
    queryKey: ["knowledge-stats"],
    queryFn: getKnowledgeStats,
  });

  const indexedDocuments = stats?.documents ?? [];
  const indexedChunks = stats?.indexed_chunks ?? 0;

  return (
    <div className="space-y-6">
      {/* Page heading */}
      <div>
        <h1 className="text-xl font-semibold text-slate-100">
          Knowledge Base
        </h1>

        <p className="mt-1 text-sm text-slate-500">
          Security knowledge that powers RAG-based explanations and
          remediation guidance.
        </p>
      </div>

      {/* Loading state */}
      {isLoading ? (
        <CardSkeleton />
      ) : isError ? (
        <div className="card p-5">
          <p className="text-sm text-red-400">
            Failed to load knowledge base statistics. Please try again.
          </p>
        </div>
      ) : (
        /* Knowledge base statistics */
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          <StatCard
            label="Indexed chunks"
            value={indexedChunks}
            icon={Layers}
          />

          <StatCard
            label="Documents"
            value={indexedDocuments.length}
            icon={Database}
          />
        </div>
      )}

      {/* Planned knowledge sources */}
      <div className="card p-5">
        <h3 className="mb-4 text-sm font-medium text-slate-300">
          Planned knowledge sources
        </h3>

        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
          {PLANNED_SOURCES.map((source) => (
            <div
              key={source}
              className="flex items-center gap-3 rounded-lg border border-border bg-surface-alt px-4 py-3"
            >
              <BookOpen className="h-4 w-4 shrink-0 text-slate-500" />

              <div>
                <p className="text-sm text-slate-200">{source}</p>

                <p className="text-xs text-slate-500">
                  Coverage not tracked yet
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Empty knowledge base state */}
      {!isLoading && !isError && indexedDocuments.length === 0 && (
        <div className="card">
          <EmptyState
            icon={Database}
            title="Knowledge base not yet ingested"
            description="Run python -m app.services.rag.ingestion from backend/ to index the Markdown knowledge files in app/services/rag/knowledge_data."
          />
        </div>
      )}

      {/* Indexed documents */}
      {!isLoading && !isError && indexedDocuments.length > 0 && (
        <div className="card p-5">
          <h3 className="mb-4 text-sm font-medium text-slate-300">
            Indexed documents
          </h3>

          <div className="flex flex-wrap gap-2">
            {indexedDocuments.map((document) => (
              <span
                key={document}
                className="badge border border-border bg-surface-alt text-slate-300"
              >
                {document}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
