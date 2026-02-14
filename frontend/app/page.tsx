"use client";

import { useMemo } from "react";
import { v4 as uuidv4 } from "uuid";

import { useChat } from "@/hooks/useChat";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import { AgentActivityPanel } from "@/components/chat/AgentActivityPanel";

export default function Home() {
  const sessionId = useMemo(() => uuidv4(), []);
  const { messages, agentActivity, isStreaming, error, sendMessage, stop } =
    useChat(sessionId);

  return (
    <div className="flex h-screen flex-col bg-background text-foreground">
      {/* Header */}
      <header className="border-b px-4 py-3">
        <div className="mx-auto flex max-w-3xl items-center justify-between">
          <h1 className="text-lg font-semibold">Velocity</h1>
          <span className="text-xs text-muted-foreground">AI PM Agent</span>
        </div>
      </header>

      {/* Agent activity badges */}
      <AgentActivityPanel activities={agentActivity} />

      {/* Error banner */}
      {error && (
        <div className="border-b border-destructive/50 bg-destructive/10 px-4 py-2">
          <p className="mx-auto max-w-3xl text-sm text-destructive">{error}</p>
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
