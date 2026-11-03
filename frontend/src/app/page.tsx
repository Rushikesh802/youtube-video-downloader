"use client";

import React, { useState } from "react";
import { useVideoMetadata } from "../hooks/useVideoMetadata";
import { URLInput } from "../components/video/URLInput";
import { VideoPreview } from "../components/video/VideoPreview";
import { FormatSelector } from "../components/video/FormatSelector";
import { DownloadButton } from "../components/video/DownloadButton";
import { ErrorAlert } from "../components/common/ErrorAlert";
import { FormatOption } from "../types/video";
import { Sparkles, Shield, Zap, RefreshCw } from "lucide-react";
import Link from "next/link";

export default function HomePage() {
  const { metadata, isLoading, error, inspect, reset } = useVideoMetadata();
  const [selectedFormat, setSelectedFormat] = useState<FormatOption | null>(null);
  const [queuedJobId, setQueuedJobId] = useState<string | null>(null);

  const handleInspect = async (url: string) => {
    setQueuedJobId(null);
    setSelectedFormat(null);
    const data = await inspect(url);
    if (data?.available_formats?.length) {
      // Auto-select 720p or 1st format
      const def =
        data.available_formats.find((f) => f.resolution === "720p") ||
        data.available_formats[0];
      setSelectedFormat(def);
    }
  };

  return (
    <div className="max-w-4xl mx-auto space-y-10">
      {/* Hero Section */}
      <div className="text-center space-y-4 pt-4 md:pt-8">
        <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-semibold bg-rose-50 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400 border border-rose-200 dark:border-rose-900 shadow-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>High-Speed Asynchronous Processing Engine</span>
        </div>

        <h1 className="text-3xl sm:text-5xl font-black text-zinc-900 dark:text-white tracking-tight leading-tight">
          Download & Transcode <br className="hidden sm:inline" />
          <span className="bg-gradient-to-r from-rose-600 to-amber-500 bg-clip-text text-transparent">
            Authorized Video & Audio
          </span>
        </h1>

        <p className="text-sm sm:text-base text-zinc-600 dark:text-zinc-400 max-w-xl mx-auto">
          Convert YouTube and licensed media streams directly into MP4, WebM, or MP3 with custom quality profiles and secure cloud delivery.
        </p>
      </div>

      {/* URL Input Form */}
      <div className="space-y-4">
        <URLInput onInspect={handleInspect} isLoading={isLoading} />
        {error && <ErrorAlert message={error} onDismiss={reset} title="Inspection Error" />}
      </div>

      {/* Queued notification banner */}
      {queuedJobId && (
        <div className="p-4 bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-900 rounded-2xl flex items-center justify-between gap-4">
          <div className="space-y-0.5">
            <h4 className="text-sm font-semibold text-emerald-800 dark:text-emerald-300">
              Job Successfully Enqueued!
            </h4>
            <p className="text-xs text-emerald-700 dark:text-emerald-400">
              Job ID: <code className="font-mono">{queuedJobId}</code> is now processing in the Celery cluster.
            </p>
          </div>
          <Link
            href="/dashboard"
            className="px-4 py-2 text-xs font-bold text-white bg-emerald-600 hover:bg-emerald-700 rounded-xl shrink-0 transition-colors shadow-sm"
          >
            Track in Dashboard
          </Link>
        </div>
      )}

      {/* Media Inspection Results */}
      {metadata && (
        <div className="space-y-6 animate-in fade-in-50 duration-300">
          <div className="flex items-center justify-between border-b border-zinc-200 dark:border-zinc-800 pb-3">
            <h3 className="text-base font-bold text-zinc-900 dark:text-white">
              Media Overview
            </h3>
            <button
              onClick={reset}
              className="flex items-center gap-1.5 text-xs text-zinc-500 hover:text-rose-600 dark:hover:text-rose-400 transition-colors"
            >
              <RefreshCw className="w-3.5 h-3.5" />
              Inspect Another
            </button>
          </div>

          <VideoPreview metadata={metadata} />

          <FormatSelector
            formats={metadata.available_formats}
            selectedFormat={selectedFormat}
            onSelect={setSelectedFormat}
          />

          <DownloadButton
            metadata={metadata}
            selectedFormat={selectedFormat}
            onSuccess={(jobId) => setQueuedJobId(jobId)}
          />
        </div>
      )}

      {/* Features Value Pillars */}
      {!metadata && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-8 border-t border-zinc-200 dark:border-zinc-800">
          <div className="p-5 bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 space-y-2">
            <div className="w-10 h-10 rounded-xl bg-blue-50 dark:bg-blue-950/40 text-blue-600 dark:text-blue-400 flex items-center justify-center">
              <Zap className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-zinc-900 dark:text-white">Distributed Workers</h4>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Celery task queues transcode video outside the API server so requests never block.
            </p>
          </div>

          <div className="p-5 bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 space-y-2">
            <div className="w-10 h-10 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 flex items-center justify-center">
              <Shield className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-zinc-900 dark:text-white">SSRF Protected</h4>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Every link is checked against DNS resolvers to prevent internal network and metadata exposure.
            </p>
          </div>

          <div className="p-5 bg-white dark:bg-zinc-900 rounded-2xl border border-zinc-200 dark:border-zinc-800 space-y-2">
            <div className="w-10 h-10 rounded-xl bg-purple-50 dark:bg-purple-950/40 text-purple-600 dark:text-purple-400 flex items-center justify-center">
              <Sparkles className="w-5 h-5" />
            </div>
            <h4 className="font-bold text-sm text-zinc-900 dark:text-white">Signed Delivery</h4>
            <p className="text-xs text-zinc-500 dark:text-zinc-400 leading-relaxed">
              Completed media is delivered using 15-minute temporary URLs and automatically purged after 24h.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
