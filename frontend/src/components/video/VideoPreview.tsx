import React from "react";
import Image from "next/image";
import { VideoMetadata } from "../../types/video";
import { formatDuration } from "../../lib/utils";
import { Clock, User } from "lucide-react";

interface VideoPreviewProps {
  metadata: VideoMetadata;
}

export function VideoPreview({ metadata }: VideoPreviewProps) {
  return (
    <div className="flex flex-col sm:flex-row gap-5 p-5 bg-white dark:bg-zinc-900 border border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-sm">
      {/* Thumbnail */}
      <div className="relative w-full sm:w-64 aspect-video rounded-xl overflow-hidden bg-zinc-100 dark:bg-zinc-800 shrink-0">
        {metadata.thumbnail_url ? (
          <Image
            src={metadata.thumbnail_url}
            alt={metadata.title}
            fill
            className="object-cover"
            sizes="(max-width: 640px) 100vw, 256px"
            unoptimized
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-zinc-400">
            No Preview
          </div>
        )}

        {/* Duration badge */}
        <div className="absolute bottom-2 right-2 bg-black/80 backdrop-blur-sm text-white text-xs px-2 py-0.5 rounded-md font-mono flex items-center gap-1">
          <Clock className="w-3 h-3" />
          {formatDuration(metadata.duration_seconds)}
        </div>
      </div>

      {/* Info */}
      <div className="flex flex-col justify-between flex-1 min-w-0">
        <div>
          <div className="flex items-center gap-2 mb-2">
            <span className="uppercase text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full bg-rose-100 text-rose-700 dark:bg-rose-950/60 dark:text-rose-300">
              {metadata.provider}
            </span>
          </div>

          <h3 className="text-base sm:text-lg font-bold text-zinc-900 dark:text-white line-clamp-2 leading-snug">
            {metadata.title}
          </h3>

          {metadata.uploader && (
            <p className="flex items-center gap-1.5 text-xs text-zinc-500 dark:text-zinc-400 mt-2">
              <User className="w-3.5 h-3.5" />
              <span>{metadata.uploader}</span>
            </p>
          )}
        </div>

        <p className="text-xs text-zinc-400 mt-4 truncate">
          Source: <span className="underline">{metadata.source_url}</span>
        </p>
      </div>
    </div>
  );
}
