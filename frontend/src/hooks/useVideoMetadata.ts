"use client";

import { useState } from "react";
import { api } from "../lib/api-client";
import { VideoMetadata } from "../types/video";

export function useVideoMetadata() {
  const [metadata, setMetadata] = useState<VideoMetadata | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const inspect = async (url: string) => {
    if (!url.trim()) {
      setError("Please enter a valid video URL.");
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const data = await api.videos.inspectMetadata(url);
      setMetadata(data);
      return data;
    } catch (err: any) {
      const msg = err.message || "Failed to inspect video URL.";
      setError(msg);
      setMetadata(null);
    } finally {
      setIsLoading(false);
    }
  };

  const reset = () => {
    setMetadata(null);
    setError(null);
    setIsLoading(false);
  };

  return {
    metadata,
    isLoading,
    error,
    inspect,
    reset,
  };
}
