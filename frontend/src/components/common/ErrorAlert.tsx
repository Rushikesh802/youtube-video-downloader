import React from "react";
import { AlertCircle, X } from "lucide-react";
import { cn } from "../../lib/utils";

interface ErrorAlertProps {
  message: string;
  onDismiss?: () => void;
  className?: string;
  title?: string;
}

export function ErrorAlert({ message, onDismiss, className, title }: ErrorAlertProps) {
  if (!message) return null;

  return (
    <div
      className={cn(
        "p-4 rounded-xl border border-rose-200 bg-rose-50/80 dark:bg-rose-950/30 dark:border-rose-900 text-rose-900 dark:text-rose-200 flex items-start gap-3 shadow-sm",
        className
      )}
    >
      <AlertCircle className="w-5 h-5 text-rose-600 dark:text-rose-400 mt-0.5 shrink-0" />
      <div className="flex-1 text-sm">
        {title && <h4 className="font-semibold text-rose-800 dark:text-rose-300 mb-0.5">{title}</h4>}
        <p className="leading-relaxed">{message}</p>
      </div>
      {onDismiss && (
        <button
          onClick={onDismiss}
          className="text-rose-400 hover:text-rose-700 dark:hover:text-rose-200 transition-colors p-1"
          aria-label="Dismiss alert"
        >
          <X className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}
