"use client";

import React, { useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "../../lib/auth-context";
import { useCreateDownloadJob } from "../../hooks/useDownloadJob";
import { FormatOption, VideoMetadata } from "../../types/video";
import { Download, Loader2, LogIn } from "lucide-react";

interface DownloadButtonProps {
  metadata: VideoMetadata;
  selectedFormat: FormatOption | null;
  onSuccess?: (jobId: string) => void;
}

export function DownloadButton({ metadata, selectedFormat, onSuccess }: DownloadButtonProps) {
  const router = useRouter();
  const { user } = useAuth();
  const createJob = useCreateDownloadJob();
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleStartDownload = async () => {
    if (!user) {
      router.push("/login?redirect=" + encodeURIComponent("/"));
      return;
    }

    if (!selectedFormat) {
      setErrorMsg("Please select a target resolution or format first.");
      return;
    }

    setErrorMsg(null);
    try {
      const result = await createJob.mutateAsync({
        mediaId: metadata.media_id,
        format: selectedFormat.format,
        resolution: selectedFormat.resolution,
      });

      if (onSuccess) {
        onSuccess(result.job_id);
      } else {
        router.push("/dashboard");
      }
    } catch (err: any) {
      setErrorMsg(err.message || "Failed to start download job.");
    }
  };

  return (
    <div className="space-y-3">
      {errorMsg && (
        <p className="text-xs text-rose-600 dark:text-rose-400 font-medium">
          {errorMsg}
        </p>
      )}

      <button
        type="button"
        onClick={handleStartDownload}
        disabled={!selectedFormat || createJob.isPending}
        className="w-full flex items-center justify-center gap-2 px-6 py-4 rounded-xl text-base font-semibold text-white bg-gradient-to-r from-rose-600 to-rose-500 hover:from-rose-700 hover:to-rose-600 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-rose-600/25 transition-all"
      >
        {createJob.isPending ? (
          <>
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Submitting Job to Queue...</span>
          </>
        ) : !user ? (
          <>
            <LogIn className="w-5 h-5" />
            <span>Login to Download</span>
          </>
        ) : (
          <>
            <Download className="w-5 h-5" />
            <span>
              Download{" "}
              {selectedFormat
                ? `${selectedFormat.resolution.toUpperCase()} (${selectedFormat.format.toUpperCase()})`
                : ""}
            </span>
          </>
        )}
      </button>
    </div>
  );
}
