"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

interface InviteFormProps {
  projectId: string;
  onInviteSent: (email: string) => void;
}

export function TeamInviteFlow({ projectId, onInviteSent }: InviteFormProps) {
  const [email, setEmail] = useState("");
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState<string[]>([]);

  const handleInvite = async () => {
    if (!email) return;
    setSending(true);
    try {
      const res = await fetch("/api/invites", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ projectId, email }),
      });
      if (res.ok) {
        setSent((prev) => [...prev, email]);
        onInviteSent(email);
        setEmail("");
      }
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-6 p-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold">Invite your team</h2>
        <p className="text-sm text-muted-foreground">
          Teams that collaborate within 48h are 3.2x more likely to succeed.
        </p>
      </div>

      <div className="flex gap-2">
        <Input
          type="email"
          placeholder="teammate@company.com"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleInvite()}
          disabled={sending}
        />
        <Button onClick={handleInvite} disabled={sending || !email}>
          {sending ? "Sending..." : "Invite"}
        </Button>
      </div>

      {sent.length > 0 && (
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Invited:</p>
          {sent.map((e) => (
            <div key={e} className="flex items-center gap-2 text-sm">
              <span className="text-emerald-500">✓</span> {e}
            </div>
          ))}
        </div>
      )}

      <Button variant="ghost" className="w-full text-muted-foreground">
        Skip for now
      </Button>
    </div>
  );
}
