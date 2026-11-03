"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api-client";
import { DownloadJob } from "../types/download";

export function useDownloadJobs() {
  const query = useQuery({
    queryKey: ["downloads"],
    queryFn: () => api.downloads.listJobs(0, 50),
    // Poll every 2 seconds if any job is currently in flight
    refetchInterval: (query) => {
      const data = query.state.data;
      const hasActive = data?.items?.some((j: DownloadJob) =>
        ["queued", "processing", "uploading"].includes(j.status)
      );
      return hasActive ? 2000 : false;
    },
  });

  return query;
}

export function useDownloadJob(jobId: string | null) {
  const query = useQuery({
    queryKey: ["download", jobId],
    queryFn: () => (jobId ? api.downloads.getJob(jobId) : null),
    enabled: !!jobId,
    refetchInterval: (query) => {
      const job = query.state.data;
      if (!job) return false;
      const isActive = ["queued", "processing", "uploading"].includes(job.status);
      return isActive ? 1500 : false;
    },
  });

  return query;
}

export function useCreateDownloadJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      mediaId,
      format,
      resolution,
    }: {
      mediaId: string;
      format: string;
      resolution: string;
    }) => api.downloads.createJob(mediaId, format, resolution),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["downloads"] });
    },
  });
}

export function useCancelDownloadJob() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (jobId: string) => api.downloads.deleteJob(jobId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["downloads"] });
      queryClient.invalidateQueries({ queryKey: ["history"] });
    },
  });
}
