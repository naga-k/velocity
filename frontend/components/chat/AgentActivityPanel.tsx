"use client";

import { Badge } from "@/components/ui/badge";
import type { AgentActivityData } from "@/lib/types";

interface AgentActivityPanelProps {
  activities: AgentActivityData[];
}

export function AgentActivityPanel({ activities }: AgentActivityPanelProps) {
  if (activities.length === 0) return null;

  return (
    <div className="border-b px-4 py-2">
      <div className="mx-auto flex max-w-3xl flex-wrap gap-2">
        {activities.map((activity) => (
          <Badge
            key={activity.agent}
            variant={activity.status === "running" ? "default" : "secondary"}
            className="text-xs"
          >
            {activity.agent}: {activity.task}
            {activity.status === "running" && (
              <span className="ml-1 animate-pulse">...</span>
            )}
          </Badge>
        ))}
      </div>
    </div>
  );
}
