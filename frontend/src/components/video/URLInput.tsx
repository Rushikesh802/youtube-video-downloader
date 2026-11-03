"use client";

import React, { useState } from "react";
import { Search, Loader2, Link2, Clipboard } from "lucide-react";

interface URLInputProps {
  onInspect: (url: string) => void;
  isLoading: boolean;
}

export function URLInput({ onInspect, isLoading }: URLInputProps) {
  const [url, setUrl] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (url.trim()) {
      onInspect(url.trim());
    }
  };

  const handlePaste = async () => {
    try {
      const text = await navigator.clipboard.readText();
      if (text) {
        setUrl(text);
        onInspect(text.trim());
      }
    } catch {
      // Clipboard read fallback if permission denied
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative flex items-center bg-white dark:bg-zinc-900 border-2 border-zinc-200 dark:border-zinc-800 rounded-2xl shadow-lg shadow-zinc-200/50 dark:shadow-none focus-within:border-rose-500 dark:focus-within:border-rose-500 transition-all p-1.5">
        <div className="pl-3 text-zinc-400">
          <Link2 className="w-5 h-5" />
        </div>

        <input
          type="url"
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="Paste authorized YouTube or media URL here..."
          className="w-full px-3 py-3 text-sm md:text-base text-zinc-900 dark:text-white bg-transparent placeholder-zinc-400 focus:outline-none"
          required
          disabled={isLoading}
        />

        <div className="flex items-center gap-1.5 pr-1.5">
          {!url && (
            <button
              type="button"
              onClick={handlePaste}
              className="hidden sm:flex items-center gap-1 px-3 py-2 text-xs font-medium text-zinc-500 hover:text-zinc-800 dark:text-zinc-400 dark:hover:text-white bg-zinc-100 dark:bg-zinc-800 hover:bg-zinc-200 dark:hover:bg-zinc-700 rounded-xl transition-colors"
            >
              <Clipboard className="w-3.5 h-3.5" />
              Paste
            </button>
          )}

          <button
            type="submit"
            disabled={isLoading || !url.trim()}
            className="flex items-center gap-2 px-5 py-3 text-sm font-semibold text-white bg-rose-600 hover:bg-rose-700 disabled:opacity-50 disabled:hover:bg-rose-600 rounded-xl shadow-md shadow-rose-600/30 transition-all"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Inspecting...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Inspect Media</span>
              </>
            )}
          </button>
        </div>
      </div>
    </form>
  );
}
