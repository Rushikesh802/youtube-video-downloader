import React from "react";
import { Loader2 } from "lucide-react";
import { cn } from "../../lib/utils";

interface LoaderProps {
  size?: "sm" | "md" | "lg";
  className?: string;
  text?: string;
}

export function Loader({ size = "md", className, text }: LoaderProps) {
  const sizeClasses = {
    sm: "w-4 h-4",
    md: "w-6 h-6",
    lg: "w-10 h-10",
  };

  return (
    <div className={cn("flex flex-col items-center justify-center p-4", className)}>
      <Loader2 className={cn("animate-spin text-rose-600", sizeClasses[size])} />
      {text && <p className="mt-2 text-sm text-zinc-500 font-medium">{text}</p>}
    </div>
  );
}

export function PageLoader({ text = "Loading..." }: { text?: string }) {
  return (
    <div className="min-h-[50vh] flex items-center justify-center">
      <Loader size="lg" text={text} />
    </div>
  );
}
