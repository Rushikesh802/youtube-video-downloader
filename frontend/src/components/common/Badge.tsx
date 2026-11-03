import React from "react";
import { DownloadStatus } from "../../types/download";
import { cn } from "../../lib/utils";
import { CheckCircle2, AlertCircle, Clock, Loader2, XCircle, TimerOff } from "lucide-react";

interface BadgeProps {
  status: DownloadStatus | string;
  className?: string;
  showIcon?: boolean;
}

export function Badge({ status, className, showIcon = true }: BadgeProps) {
  const normalized = status.toLowerCase();

  const config: Record<
    string,
    { label: string; bg: string; text: string; border: string; icon: React.ReactNode }
  > = {
    queued: {
      label: "Queued",
      bg: "bg-amber-50 dark:bg-amber-950/40",
      text: "text-amber-700 dark:text-amber-300",
      border: "border-amber-200 dark:border-amber-800",
      icon: <Clock className="w-3.5 h-3.5 mr-1 animate-pulse" />,
    },
    processing: {
      label: "Processing",
      bg: "bg-blue-50 dark:bg-blue-950/40",
      text: "text-blue-700 dark:text-blue-300",
      border: "border-blue-200 dark:border-blue-800",
      icon: <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />,
    },
    uploading: {
      label: "Uploading",
      bg: "bg-indigo-50 dark:bg-indigo-950/40",
      text: "text-indigo-700 dark:text-indigo-300",
      border: "border-indigo-200 dark:border-indigo-800",
      icon: <Loader2 className="w-3.5 h-3.5 mr-1 animate-spin" />,
    },
    completed: {
      label: "Completed",
      bg: "bg-emerald-50 dark:bg-emerald-950/40",
      text: "text-emerald-700 dark:text-emerald-300",
      border: "border-emerald-200 dark:border-emerald-800",
      icon: <CheckCircle2 className="w-3.5 h-3.5 mr-1" />,
    },
    failed: {
      label: "Failed",
      bg: "bg-rose-50 dark:bg-rose-950/40",
      text: "text-rose-700 dark:text-rose-300",
      border: "border-rose-200 dark:border-rose-800",
      icon: <AlertCircle className="w-3.5 h-3.5 mr-1" />,
    },
    expired: {
      label: "Expired",
      bg: "bg-zinc-100 dark:bg-zinc-800",
      text: "text-zinc-600 dark:text-zinc-400",
      border: "border-zinc-300 dark:border-zinc-700",
      icon: <TimerOff className="w-3.5 h-3.5 mr-1" />,
    },
    cancelled: {
      label: "Cancelled",
      bg: "bg-zinc-100 dark:bg-zinc-800",
      text: "text-zinc-600 dark:text-zinc-400",
      border: "border-zinc-300 dark:border-zinc-700",
      icon: <XCircle className="w-3.5 h-3.5 mr-1" />,
    },
  };

  const style = config[normalized] || {
    label: status,
    bg: "bg-zinc-100",
    text: "text-zinc-800",
    border: "border-zinc-200",
    icon: null,
  };

  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        style.bg,
        style.text,
        style.border,
        className
      )}
    >
      {showIcon && style.icon}
      {style.label}
    </span>
  );
}
