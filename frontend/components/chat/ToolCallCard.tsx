"use client";

import { Code2, Database, MessageSquare, Search } from "lucide-react";

interface ToolCallCardProps {
  tool: string;
  params?: Record<string, unknown>;
  result?: string;
}

const TOOL_ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
  slack: MessageSquare,
  linear: Database,
  search: Search,
  default: Code2,
};

export function ToolCallCard({ tool, params, result }: ToolCallCardProps) {
  const IconComponent = TOOL_ICONS[tool.toLowerCase()] || TOOL_ICONS.default;

  return (
    <div className="my-2 animate-in fade-in zoom-in-95 duration-200 rounded-lg border border-border/50 bg-gradient-to-br from-muted/30 to-muted/10 p-3">
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-primary/10 p-2">
          <IconComponent className="h-4 w-4 text-primary" />
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-foreground">
              {tool}
            </span>
            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] font-medium text-green-600 dark:text-green-400">
              executed
            </span>
          </div>

          {params && Object.keys(params).length > 0 && (
            <div className="mt-2 space-y-1">
              {Object.entries(params).slice(0, 3).map(([key, value]) => (
                <div key={key} className="flex items-start gap-2 text-xs">
                  <span className="text-muted-foreground">{key}:</span>
                  <span className="font-mono text-foreground/80">
                    {typeof value === "string" ? value : JSON.stringify(value)}
                  </span>
                </div>
              ))}
            </div>
          )}

          {result && (
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
              → {result}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
