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

  const sendMessage = useCallback(
    async (content: string) => {
      if (!content.trim()) return;

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
        const response = await sendChatMessage(
          { message: content, session_id: sessionId },
          abortRef.current.signal
        );

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body!.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        let currentEventType: SSEEventType | null = null;

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          buffer += decoder.decode(value, { stream: true });
          const lines = buffer.split("\n");
          buffer = lines.pop() || "";

          for (const line of lines) {
            if (line.startsWith("event:")) {
              currentEventType = line.slice(6).trim() as SSEEventType;
              continue;
            }

            if (line.startsWith("data:") && currentEventType) {
              const rawData = line.slice(5).trim();
              try {
                const data = JSON.parse(rawData);

                switch (currentEventType) {
                  case "text": {
                    // data is a bare string
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
                    // Mark assistant message as done streaming
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

                  // thinking, citation, tool_call — handled by Track A/B
                  default:
                    break;
                }
              } catch {
                // Skip malformed JSON
              }
              currentEventType = null;
            }

            // Empty line resets event state (SSE spec)
            if (line === "") {
              currentEventType = null;
            }
          }
        }
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") {
          // User cancelled — not an error
        } else {
          setError(err instanceof Error ? err.message : "Unknown error");
        }
      } finally {
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
