import React from "react";
import { FormatOption } from "../../types/video";
import { formatBytes } from "../../lib/utils";
import { Video, Music, Check } from "lucide-react";
import { cn } from "../../lib/utils";

interface FormatSelectorProps {
  formats: FormatOption[];
  selectedFormat: FormatOption | null;
  onSelect: (format: FormatOption) => void;
}

export function FormatSelector({ formats, selectedFormat, onSelect }: FormatSelectorProps) {
  if (!formats || formats.length === 0) {
    return (
      <div className="p-4 text-center text-sm text-zinc-400">
        No output formats available for this media.
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <h4 className="text-sm font-semibold text-zinc-700 dark:text-zinc-300">
        Select Target Quality & Format
      </h4>

      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-3">
        {formats.map((option, idx) => {
          const isSelected =
            selectedFormat?.format === option.format &&
            selectedFormat?.resolution === option.resolution;

          return (
            <button
              key={`${option.format}-${option.resolution}-${idx}`}
              type="button"
              onClick={() => onSelect(option)}
              className={cn(
                "relative flex items-center justify-between p-3.5 rounded-xl border text-left transition-all",
                isSelected
                  ? "border-rose-500 bg-rose-50/50 dark:bg-rose-950/20 ring-2 ring-rose-500/20 shadow-sm"
                  : "border-zinc-200 dark:border-zinc-800 bg-white dark:bg-zinc-900 hover:border-zinc-300 dark:hover:border-zinc-700"
              )}
            >
              <div className="flex items-center gap-3 min-w-0">
                <div
                  className={cn(
                    "w-9 h-9 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                    option.is_audio_only
                      ? "bg-purple-100 dark:bg-purple-950/50 text-purple-600 dark:text-purple-400"
                      : "bg-rose-100 dark:bg-rose-950/50 text-rose-600 dark:text-rose-400"
                  )}
                >
                  {option.is_audio_only ? (
                    <Music className="w-4 h-4" />
                  ) : (
                    <Video className="w-4 h-4" />
                  )}
                </div>

                <div className="min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="font-bold text-sm text-zinc-900 dark:text-white uppercase">
                      {option.resolution === "audio_only" ? "MP3 Audio" : option.resolution}
                    </span>
                    <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded uppercase bg-zinc-100 dark:bg-zinc-800 text-zinc-600 dark:text-zinc-400">
                      {option.file_extension}
                    </span>
                  </div>

                  <p className="text-xs text-zinc-400 truncate mt-0.5">
                    {option.approx_file_size
                      ? `~${formatBytes(option.approx_file_size)}`
                      : option.description}
                  </p>
                </div>
              </div>

              {isSelected && (
                <div className="w-5 h-5 rounded-full bg-rose-600 text-white flex items-center justify-center shrink-0">
                  <Check className="w-3 h-3 stroke-[3]" />
                </div>
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
}
