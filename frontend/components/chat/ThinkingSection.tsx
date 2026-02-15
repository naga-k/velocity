"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight } from "lucide-react";

interface ThinkingSectionProps {
  thinking: string;
  agent?: string;
}

export function ThinkingSection({ thinking, agent }: ThinkingSectionProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <div className="my-2 animate-in fade-in slide-in-from-top-1 duration-200">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex w-full items-center gap-2 rounded-lg border border-border/50 bg-muted/30 px-3 py-2 text-left text-xs transition-colors hover:bg-muted/50"
      >
        {isExpanded ? (
          <ChevronDown className="h-3 w-3 text-muted-foreground" />
        ) : (
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        )}
        <span className="font-medium text-foreground">
          💭 {agent || "Agent"} thinking...
        </span>
      </button>

      {isExpanded && (
        <div className="mt-2 animate-in fade-in slide-in-from-top-1 duration-150 rounded-lg border border-border/30 bg-muted/20 p-3">
          <p className="text-xs italic leading-relaxed text-muted-foreground">
            {thinking}
          </p>
        </div>
      )}
    </div>
  );
}
