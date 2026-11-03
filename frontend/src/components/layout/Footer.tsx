import React from "react";
import { ShieldCheck, HardDrive, Cpu } from "lucide-react";

export function Footer() {
  return (
    <footer className="w-full border-t border-zinc-200 dark:border-zinc-800 bg-zinc-50 dark:bg-zinc-950 py-8 transition-colors">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-sm text-zinc-500 dark:text-zinc-400">
          <span>&copy; {new Date().getFullYear()} MediaStream Downloader. Authorized media only.</span>
        </div>

        <div className="flex items-center gap-6 text-xs text-zinc-400 dark:text-zinc-500 font-medium">
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-4 h-4 text-emerald-500" />
            SSRF Guard Enabled
          </span>
          <span className="flex items-center gap-1.5">
            <Cpu className="w-4 h-4 text-blue-500" />
            Celery & FFmpeg Distributed
          </span>
          <span className="flex items-center gap-1.5">
            <HardDrive className="w-4 h-4 text-purple-500" />
            S3 & 15m Signed URLs
          </span>
        </div>
      </div>
    </footer>
  );
}
