"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "../../lib/auth-context";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../../lib/api-client";
import { DownloadHistoryTable } from "../../components/downloads/DownloadHistoryTable";
import { PageLoader } from "../../components/common/Loader";
import { History, RefreshCw, LogIn } from "lucide-react";

export default function HistoryPage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const queryClient = useQueryClient();

  const { data, isLoading, refetch, isRefetching } = useQuery({
    queryKey: ["history"],
    queryFn: () => api.history.listHistory(0, 50),
    enabled: !!user,
  });

  if (isAuthLoading) {
    return <PageLoader text="Verifying authentication..." />;
  }

  if (!user) {
    return (
      <div className="max-w-md mx-auto text-center py-20 px-4 space-y-4">
        <div className="w-14 h-14 mx-auto rounded-2xl bg-rose-50 dark:bg-rose-950/40 text-rose-600 flex items-center justify-center mb-2">
          <LogIn className="w-7 h-7" />
        </div>
        <h2 className="text-xl font-bold text-zinc-900 dark:text-white">
          Sign in required
        </h2>
        <p className="text-xs text-zinc-500 dark:text-zinc-400">
          Please log in to view your complete media download history and audit records.
        </p>
        <Link
          href="/login?redirect=/history"
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 transition-all shadow-md shadow-rose-600/25"
        >
          Sign In
        </Link>
      </div>
    );
  }

  const items = data?.items || [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <History className="w-6 h-6 text-rose-600" />
            <h1 className="text-2xl font-black text-zinc-900 dark:text-white tracking-tight">
              Download History
            </h1>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Audit trail of all converted and downloaded files associated with your account
          </p>
        </div>

        <button
          onClick={() => refetch()}
          disabled={isRefetching}
          className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-sm self-start sm:self-auto"
          title="Refresh history"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin text-rose-600" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* History Table */}
      <DownloadHistoryTable
        items={items}
        isLoading={isLoading}
        onItemDeleted={() => queryClient.invalidateQueries({ queryKey: ["history"] })}
      />
    </div>
  );
}
