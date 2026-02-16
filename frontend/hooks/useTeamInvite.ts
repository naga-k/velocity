import { useState, useCallback } from "react";

interface Invite {
  email: string;
  status: "pending" | "accepted" | "expired";
  sentAt: string;
}

export function useTeamInvite(projectId: string) {
  const [invites, setInvites] = useState<Invite[]>([]);
  const [loading, setLoading] = useState(false);

  const sendInvite = useCallback(
    async (email: string) => {
      setLoading(true);
      try {
        const res = await fetch("/api/invites", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ projectId, email }),
        });
        if (!res.ok) throw new Error("Failed to send invite");
        const data = await res.json();
        setInvites((prev) => [
          ...prev,
          { email, status: "pending", sentAt: new Date().toISOString() },
        ]);
        return data;
      } finally {
        setLoading(false);
      }
    },
    [projectId]
  );

  const fetchInvites = useCallback(async () => {
    const res = await fetch(`/api/invites?projectId=${projectId}`);
    if (res.ok) {
      const data = await res.json();
      setInvites(data.invites);
    }
  }, [projectId]);

  return { invites, loading, sendInvite, fetchInvites };
}
