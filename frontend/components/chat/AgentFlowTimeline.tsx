"use client";

import { Badge } from "@/components/ui/badge";
import type { AgentActivityData } from "@/lib/types";

interface AgentFlowTimelineProps {
  activities: AgentActivityData[];
}

export function AgentFlowTimeline({ activities }: AgentFlowTimelineProps) {
  if (activities.length === 0) return null;

  return (
    <div className="border-b bg-gradient-to-r from-background via-muted/20 to-background px-4 py-3">
      <div className="mx-auto max-w-3xl">
        {/* Timeline flow */}
        <div className="flex items-center gap-2 overflow-x-auto pb-2">
          {activities.map((activity, idx) => (
            <div key={activity.agent} className="flex items-center gap-2 shrink-0">
              {/* Agent badge with glow effect */}
              <div className="relative">
                {activity.status === "running" && (
                  <div className="absolute inset-0 animate-pulse rounded-full bg-primary/20 blur-md" />
                )}
                <Badge
                  variant={activity.status === "running" ? "default" : "secondary"}
                  className="relative text-xs font-semibold"
                >
                  <span className="mr-1.5">
                    {activity.status === "running" ? "🧠" : "✓"}
                  </span>
                  {activity.agent}
                </Badge>
              </div>

              {/* Arrow connector */}
              {idx < activities.length - 1 && (
                <svg
                  className="h-4 w-4 text-muted-foreground"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9 5l7 7-7 7"
                  />
                </svg>
              )}
            </div>
          ))}
        </div>

        {/* Current task with typewriter effect */}
        {activities.some((a) => a.status === "running") && (
          <div className="mt-2 animate-in fade-in slide-in-from-bottom-2 duration-300">
            <p className="text-sm text-muted-foreground">
              <span className="font-medium text-foreground">
                {activities.find((a) => a.status === "running")?.agent}:
              </span>{" "}
              {activities.find((a) => a.status === "running")?.task}
            </p>
            {activities.find((a) => a.status === "running")?.thinking && (
              <p className="mt-1 text-xs italic text-muted-foreground/80">
                💭 {activities.find((a) => a.status === "running")?.thinking}
              </p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
