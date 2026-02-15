"use client";

import { useMemo } from "react";
import { v4 as uuidv4 } from "uuid";

import { useChat } from "@/hooks/useChat";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import { AgentFlowTimeline } from "@/components/chat/AgentFlowTimeline";

export default function Home() {
  const sessionId = useMemo(() => uuidv4(), []);
  const { messages, agentActivity, isStreaming, error, sendMessage, stop } =
    useChat(sessionId);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Header with gradient */}
      <header className="border-b bg-gradient-to-r from-background via-muted/10 to-background px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-purple-600">
              <span className="text-lg">⚡</span>
            </div>
            <h1 className="text-lg font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
              Velocity
            </h1>
          </div>
          <span className="text-xs font-medium text-muted-foreground">
            AI PM Agent
          </span>
        </div>
      </header>

      {/* Agent flow timeline */}
      <AgentFlowTimeline activities={agentActivity} />

      {/* Error banner with animation */}
      {error && (
        <div className="animate-in slide-in-from-top-2 duration-200 border-b border-destructive/50 bg-gradient-to-r from-destructive/10 via-destructive/15 to-destructive/10 px-4 py-2.5">
          <div className="mx-auto max-w-3xl flex items-center gap-2">
            <span className="text-destructive">⚠️</span>
            <p className="text-sm font-medium text-destructive">{error}</p>
          </div>
        </div>
      )}

      {/* Messages */}
      <ChatMessages messages={messages} />

      {/* Input */}
      <ChatInput
        onSend={sendMessage}
        onStop={stop}
        isStreaming={isStreaming}
      />
    </div>
  );
}
