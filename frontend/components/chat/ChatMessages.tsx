"use client";

import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import rehypeHighlight from "rehype-highlight";
import "highlight.js/styles/github-dark.css";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import type { Message } from "@/lib/types";
import { ToolCallCard } from "./ToolCallCard";
import { ThinkingSection } from "./ThinkingSection";

interface ChatMessagesProps {
  messages: Message[];
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"} animate-in fade-in slide-in-from-bottom-3 duration-500`}
    >
      {/* Avatar with glow effect */}
      <Avatar className="h-8 w-8 shrink-0 relative">
        {!isUser && message.isStreaming && (
          <div className="absolute inset-0 animate-pulse rounded-full bg-gradient-to-br from-primary/30 to-purple-500/30 blur-sm" />
        )}
        <div
          className={`flex h-full w-full items-center justify-center rounded-full text-xs font-bold relative ${
            isUser
              ? "bg-gradient-to-br from-primary to-primary/80 text-primary-foreground"
              : "bg-gradient-to-br from-muted to-muted/60 text-foreground"
          }`}
        >
          {isUser ? "U" : "V"}
        </div>
      </Avatar>

      <div className={`max-w-[80%] ${isUser ? "" : "space-y-2"}`}>
        {/* Thinking section (collapsible) */}
        {!isUser && message.thinking && (
          <ThinkingSection thinking={message.thinking} />
        )}

        {/* Tool calls */}
        {!isUser && message.toolCalls && message.toolCalls.length > 0 && (
          <div className="space-y-1.5">
            {message.toolCalls.map((tc, idx) => (
              <ToolCallCard key={idx} tool={tc.tool} params={tc.params} />
            ))}
          </div>
        )}

        {/* Message card with gradient */}
        <div
          className={`rounded-xl px-4 py-3 shadow-sm transition-all ${
            isUser
              ? "bg-gradient-to-br from-primary via-primary/95 to-primary/80 text-primary-foreground"
              : "bg-gradient-to-br from-muted/50 via-muted/40 to-muted/30 text-foreground border border-border/50 hover:border-border/70"
          }`}
        >
          {message.content ? (
            isUser ? (
              <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
            ) : (
              <div className="prose prose-sm dark:prose-invert max-w-none prose-headings:font-semibold prose-p:leading-relaxed prose-li:leading-relaxed">
                <ReactMarkdown remarkPlugins={[remarkGfm]} rehypePlugins={[rehypeHighlight]}>
                  {message.content}
                </ReactMarkdown>
              </div>
            )
          ) : message.isStreaming ? (
            <div className="flex flex-col gap-2 py-1">
              <Skeleton className="h-3 w-48 animate-pulse" />
              <Skeleton className="h-3 w-32 animate-pulse" style={{ animationDelay: "150ms" }} />
            </div>
          ) : null}
        </div>

        {/* Citations with stagger animation */}
        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="space-y-1.5">
            {message.citations.map((citation, idx) => (
              <a
                key={idx}
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="group block animate-in fade-in slide-in-from-bottom-2 duration-300 rounded-lg border border-border/50 bg-gradient-to-br from-card via-card/80 to-card/50 px-3 py-2.5 text-xs transition-all hover:border-primary/40 hover:shadow-md hover:-translate-y-0.5"
                style={{ animationDelay: `${idx * 75}ms` }}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="inline-flex items-center gap-1.5 rounded-md bg-primary/10 px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-primary">
                        {citation.type === "slack" && "💬"}
                        {citation.type === "linear" && "📋"}
                        {citation.type === "web" && "🌐"}
                        {citation.type}
                      </span>
                    </div>
                    <p className="font-semibold text-foreground/90 leading-snug mb-1.5">
                      {citation.title}
                    </p>
                    {citation.snippet && (
                      <p className="text-muted-foreground/80 leading-relaxed line-clamp-2">
                        {citation.snippet}
                      </p>
                    )}
                  </div>
                  <svg
                    className="h-4 w-4 shrink-0 text-muted-foreground transition-transform group-hover:translate-x-0.5 group-hover:-translate-y-0.5"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                    />
                  </svg>
                </div>
              </a>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export function ChatMessages({ messages }: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <div className="text-center text-muted-foreground animate-in fade-in zoom-in-95 duration-700">
          <div className="mb-4 inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-purple-500/20">
            <span className="text-3xl">⚡</span>
          </div>
          <h2 className="mb-2 text-xl font-bold bg-gradient-to-r from-foreground to-foreground/70 bg-clip-text text-transparent">
            Velocity
          </h2>
          <p className="text-sm leading-relaxed">
            Your AI product management assistant.
            <br />
            Ask about sprints, priorities, or backlog.
          </p>
        </div>
      </div>
    );
  }

  return (
    <ScrollArea className="flex-1">
      <div className="mx-auto max-w-3xl space-y-6 p-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
