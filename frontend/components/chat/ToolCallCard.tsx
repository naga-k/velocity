"use client";

import { useState } from "react";
import {
  Code2,
  Database,
  MessageSquare,
  Search,
  BarChart3,
  FileText,
  GitPullRequest,
  ChevronDown,
  ChevronRight,
  Zap,
} from "lucide-react";

interface ToolCallCardProps {
  tool: string;
  params?: Record<string, unknown>;
  result?: string;
}

interface ToolCallGroupProps {
  toolCalls: { tool: string; params?: Record<string, unknown> }[];
}

/** Match icon based on substrings in the tool name */
function getToolIcon(tool: string) {
  const t = tool.toLowerCase();
  if (t.includes("slack")) return MessageSquare;
  if (t.includes("linear")) return Database;
  if (t.includes("search") || t.includes("web")) return Search;
  if (t.includes("amplitude") || t.includes("metric")) return BarChart3;
  if (t.includes("notion") || t.includes("prd") || t.includes("doc") || t.includes("stakeholder"))
    return FileText;
  if (t.includes("code") || t.includes("pr") || t.includes("generate_code"))
    return GitPullRequest;
  if (t.includes("rice") || t.includes("priorit") || t.includes("scoring") || t.includes("effort"))
    return Zap;
  return Code2;
}

/** Strip mcp__pm_tools__ or mcp__slack__ prefix for clean display */
function cleanToolName(tool: string): string {
  return tool
    .replace(/^mcp__pm_tools__/, "")
    .replace(/^mcp__slack__/, "slack.");
}

/** Single compact tool call row */
function ToolCallRow({ tool, params }: ToolCallCardProps) {
  const Icon = getToolIcon(tool);
  const displayName = cleanToolName(tool);

  // Get the most meaningful param value for inline preview
  const previewParam = params
    ? Object.entries(params)
        .filter(([, v]) => v !== undefined && v !== null && v !== "")
        .slice(0, 1)
        .map(([k, v]) => `${k}: ${typeof v === "string" ? v : JSON.stringify(v)}`)
        .join("")
    : "";

  return (
    <div className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-md hover:bg-muted/30 transition-colors group">
      <div className="rounded bg-primary/8 p-1">
        <Icon className="h-3 w-3 text-primary/70" />
      </div>
      <span className="font-mono text-[11px] font-medium text-foreground/80">
        {displayName}
      </span>
      {previewParam && (
        <span className="text-[10px] text-muted-foreground/60 truncate max-w-[200px]">
          {previewParam}
        </span>
      )}
      <span className="ml-auto rounded-full bg-emerald-500/10 px-1.5 py-0.5 text-[9px] font-medium text-emerald-500 dark:text-emerald-400 opacity-60">
        done
      </span>
    </div>
  );
}

/** Collapsible group of tool calls — shows first 3, collapses rest */
export function ToolCallGroup({ toolCalls }: ToolCallGroupProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const PREVIEW_COUNT = 3;
  const hasMore = toolCalls.length > PREVIEW_COUNT;
  const hiddenCount = toolCalls.length - PREVIEW_COUNT;

  const visibleCalls = isExpanded
    ? toolCalls
    : toolCalls.slice(0, PREVIEW_COUNT);

  return (
    <div className="my-2 animate-in fade-in zoom-in-95 duration-200 rounded-lg border border-border/40 bg-muted/15 overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2 border-b border-border/30">
        <div className="flex h-5 w-5 items-center justify-center rounded bg-primary/10">
          <Code2 className="h-3 w-3 text-primary/70" />
        </div>
        <span className="text-[11px] font-semibold text-foreground/70 uppercase tracking-wider">
          {toolCalls.length} tool{toolCalls.length !== 1 ? "s" : ""} executed
        </span>
      </div>

      {/* Tool rows */}
      <div className="py-1">
        {visibleCalls.map((tc, idx) => (
          <ToolCallRow key={idx} tool={tc.tool} params={tc.params} />
        ))}
      </div>

      {/* Expand/collapse toggle */}
      {hasMore && (
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex w-full items-center justify-center gap-1.5 border-t border-border/30 px-3 py-1.5 text-[10px] font-medium text-muted-foreground hover:text-foreground hover:bg-muted/20 transition-colors"
        >
          {isExpanded ? (
            <>
              <ChevronDown className="h-3 w-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronRight className="h-3 w-3" />
              {hiddenCount} more tool{hiddenCount !== 1 ? "s" : ""}
            </>
          )}
        </button>
      )}
    </div>
  );
}

/** Single tool call card — kept for backwards compat but prefer ToolCallGroup */
export function ToolCallCard({ tool, params, result }: ToolCallCardProps) {
  const Icon = getToolIcon(tool);
  const displayName = cleanToolName(tool);

  return (
    <div className="my-2 animate-in fade-in zoom-in-95 duration-200 rounded-lg border border-border/50 bg-gradient-to-br from-muted/30 to-muted/10 p-3">
      <div className="flex items-start gap-3">
        <div className="rounded-md bg-primary/10 p-2">
          <Icon className="h-4 w-4 text-primary" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-mono text-xs font-semibold text-foreground">
              {displayName}
            </span>
            <span className="rounded-full bg-green-500/10 px-2 py-0.5 text-[10px] font-medium text-green-600 dark:text-green-400">
              executed
            </span>
          </div>
          {params && Object.keys(params).length > 0 && (
            <div className="mt-2 space-y-1">
              {Object.entries(params)
                .slice(0, 3)
                .map(([key, value]) => (
                  <div key={key} className="flex items-start gap-2 text-xs">
                    <span className="text-muted-foreground">{key}:</span>
                    <span className="font-mono text-foreground/80">
                      {typeof value === "string"
                        ? value
                        : JSON.stringify(value)}
                    </span>
                  </div>
                ))}
            </div>
          )}
          {result && (
            <p className="mt-2 text-xs text-muted-foreground line-clamp-2">
              {result}
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
