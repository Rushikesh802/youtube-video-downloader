"use client";

import React from "react";
import Link from "next/link";
import { useAuth } from "../../lib/auth-context";
import { useDownloadJobs, useCancelDownloadJob } from "../../hooks/useDownloadJob";
import { DownloadQueue } from "../../components/downloads/DownloadQueue";
import { PageLoader } from "../../components/common/Loader";
import { LayoutDashboard, Plus, RefreshCw, LogIn } from "lucide-react";

export default function DashboardPage() {
  const { user, isLoading: isAuthLoading } = useAuth();
  const { data, isLoading: isJobsLoading, refetch, isRefetching } = useDownloadJobs();
  const cancelMutation = useCancelDownloadJob();

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
          Please log in to view and manage your active download processing queue.
        </p>
        <Link
          href="/login?redirect=/dashboard"
          className="inline-flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 transition-all shadow-md shadow-rose-600/25"
        >
          Sign In
        </Link>
      </div>
    );
  }

  const jobs = data?.items || [];
  const activeCount = jobs.filter((j) =>
    ["queued", "processing", "uploading"].includes(j.status)
  ).length;

  return (
    <div className="space-y-8">
      {/* Dashboard Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-zinc-200 dark:border-zinc-800 pb-5">
        <div>
          <div className="flex items-center gap-2.5">
            <LayoutDashboard className="w-6 h-6 text-rose-600" />
            <h1 className="text-2xl font-black text-zinc-900 dark:text-white tracking-tight">
              Downloads Dashboard
            </h1>
          </div>
          <p className="text-xs text-zinc-500 dark:text-zinc-400 mt-1">
            Real-time status of your media conversion jobs • {activeCount} active job{activeCount !== 1 ? "s" : ""}
          </p>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium text-zinc-700 dark:text-zinc-300 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-xl hover:bg-zinc-50 dark:hover:bg-zinc-800 transition-colors shadow-sm"
            title="Refresh jobs"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? "animate-spin text-rose-600" : ""}`} />
            <span>Refresh</span>
          </button>

          <Link
            href="/"
            className="flex items-center gap-1.5 px-4 py-2 text-xs font-semibold text-white bg-rose-600 hover:bg-rose-700 rounded-xl shadow-md shadow-rose-600/25 transition-all"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>New Download</span>
          </Link>
        </div>
      </div>

      {/* Queue */}
      <DownloadQueue
        jobs={jobs}
        isLoading={isJobsLoading}
        onCancelJob={(jobId) => cancelMutation.mutate(jobId)}
      />
    </div>
  );
}
