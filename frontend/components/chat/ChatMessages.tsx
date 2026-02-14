"use client";

import { useEffect, useRef } from "react";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Avatar } from "@/components/ui/avatar";
import { Skeleton } from "@/components/ui/skeleton";
import type { Message } from "@/lib/types";

interface ChatMessagesProps {
  messages: Message[];
}

function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div
      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
    >
      <Avatar className="h-8 w-8 shrink-0">
        <div
          className={`flex h-full w-full items-center justify-center rounded-full text-xs font-medium ${
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted text-muted-foreground"
          }`}
        >
          {isUser ? "U" : "V"}
        </div>
      </Avatar>

      <div
        className={`max-w-[80%] rounded-lg px-4 py-2 ${
          isUser
            ? "bg-primary text-primary-foreground"
            : "bg-muted text-foreground"
        }`}
      >
        {message.content ? (
          <p className="whitespace-pre-wrap text-sm">{message.content}</p>
        ) : message.isStreaming ? (
          <div className="flex flex-col gap-2 py-1">
            <Skeleton className="h-3 w-48" />
            <Skeleton className="h-3 w-32" />
          </div>
        ) : null}
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
        <div className="text-center text-muted-foreground">
          <h2 className="mb-2 text-lg font-semibold">Velocity</h2>
          <p className="text-sm">
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
      <div className="mx-auto max-w-3xl space-y-4 p-4">
        {messages.map((msg) => (
          <MessageBubble key={msg.id} message={msg} />
        ))}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  );
}
