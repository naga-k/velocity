"use client";

import { useCallback, useRef, useState } from "react";
import { v4 as uuidv4 } from "uuid";

import { sendChatMessage } from "@/lib/api";
import type {
  AgentActivityData,
  DoneEventData,
  ErrorEventData,
  Message,
  SSEEventType,
  TokenUsage,
  ToolCallData,
} from "@/lib/types";

interface UseChatReturn {
  messages: Message[];
  agentActivity: AgentActivityData[];
  isStreaming: boolean;
  error: string | null;
  tokenUsage: TokenUsage | null;
  sendMessage: (content: string) => Promise<void>;
  stop: () => void;
}

export function useChat(sessionId: string): UseChatReturn {
  const [messages, setMessages] = useState<Message[]>([]);
  const [agentActivity, setAgentActivity] = useState<AgentActivityData[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [tokenUsage, setTokenUsage] = useState<TokenUsage | null>(null);
  const abortRef = useRef<AbortController | null>(null);
  const isStreamingRef = useRef(false);

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim() || isStreamingRef.current) return;

      isStreamingRef.current = true;
      setIsStreaming(true);
      setError(null);
      setAgentActivity([]);

      // Add user message
      const userMsg: Message = {
        id: uuidv4(),
        role: "user",
        content,
        citations: [],
      };

      // Create assistant placeholder
      const assistantId = uuidv4();
      let assistantContent = "";

      setMessages((prev) => [
        ...prev,
        userMsg,
        {
          id: assistantId,
          role: "assistant",
          content: "",
          citations: [],
          isStreaming: true,
        },
      ]);

      try {
        abortRef.current = new AbortController();

        // Set a longer timeout for Daytona sandbox creation + multi-agent workflows (3 minutes)
        const timeoutId = setTimeout(() => abortRef.current?.abort(), 180000);

        const response = await sendChatMessage(
          { message: content, session_id: sessionId },
          abortRef.current.signal
        );

        clearTimeout(timeoutId);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        if (!response.body) {
          throw new Error("Response body is null");
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentEventType: SSEEventType | null = null;
        let dataLines: string[] = [];

        const dispatchEvent = () => {
          if (!currentEventType || dataLines.length === 0) {
            currentEventType = null;
            dataLines = [];
            return;
          }

          const rawData = dataLines.join("\n");
          dataLines = [];
          const eventType = currentEventType;
          currentEventType = null;

          try {
            const data = JSON.parse(rawData);

            switch (eventType) {
              case "text": {
                if (typeof data === "string") {
                  assistantContent += data;
                  setMessages((prev) =>
                    prev.map((m) =>
                      m.id === assistantId
                        ? { ...m, content: assistantContent }
                        : m
                    )
                  );
                }
                break;
              }

              case "error": {
                const errData = data as ErrorEventData;
                setError(errData.message);
                break;
              }

              case "done": {
                const doneData = data as DoneEventData;
                setTokenUsage(doneData.tokens_used);
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId ? { ...m, isStreaming: false } : m
                  )
                );
                break;
              }

              case "agent_activity": {
                const activity = data as AgentActivityData;
                setAgentActivity((prev) => {
                  const existing = prev.findIndex(
                    (a) => a.agent === activity.agent
                  );
                  if (existing >= 0) {
                    const updated = [...prev];
                    updated[existing] = activity;
                    return updated;
                  }
                  return [...prev, activity];
                });
                break;
              }

              case "citation": {
                // Add citation to current assistant message
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? { ...m, citations: [...(m.citations || []), data] }
                      : m
                  )
                );
                break;
              }

              case "thinking": {
                const thinkingData = data as { text: string };
                // Store thinking text in current agent activity
                setAgentActivity((prev) => {
                  if (prev.length === 0) return prev;
                  const updated = [...prev];
                  const lastAgent = updated[updated.length - 1];
                  if (lastAgent.status === "running") {
                    lastAgent.thinking = thinkingData.text;
                  }
                  return updated;
                });
                break;
              }

              case "tool_call": {
                const toolCall = data as ToolCallData;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantId
                      ? {
                          ...m,
                          toolCalls: [...(m.toolCalls || []), toolCall],
                        }
                      : m
                  )
                );
                break;
              }

              default:
                break;
            }
          } catch {
            // Skip malformed JSON
          }
        };

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const rawLine of lines) {
            // Strip trailing \r from \r\n line endings (SSE spec allows both)
            const line = rawLine.endsWith("\r")
              ? rawLine.slice(0, -1)
              : rawLine;

            if (line.startsWith("event:")) {
              currentEventType = line.slice(6).trim() as SSEEventType;
              continue;
            }

            if (line.startsWith("data:")) {
              dataLines.push(line.slice(5).trim());
              continue;
            }

            // Empty line dispatches the event (SSE spec)
            if (line === "") {
              dispatchEvent();
            }
          }
        }

        // Flush remaining buffer and dispatch any pending event
        if (buffer.trim()) {
          if (buffer.startsWith("data:")) {
            dataLines.push(buffer.slice(5).trim());
          }
        }
        dispatchEvent();
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // User cancelled — not an error
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
        isStreamingRef.current = false;
        setIsStreaming(false);
        // Ensure assistant message is marked as not streaming
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId ? { ...m, isStreaming: false } : m
          )
        );
      }
    },
    [sessionId]
  );

  const stop = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  return {
    messages,
    agentActivity,
    isStreaming,
    error,
    tokenUsage,
    sendMessage,
    stop,
  };
}
