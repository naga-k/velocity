/**
 * API client for Velocity backend.
 *
 * All requests go through the Next.js rewrite proxy (/api/* → backend:8000/api/*).
 */

import type {
  ChatRequest,
  HealthResponse,
  SessionCreate,
  SessionResponse,
} from "./types";

const API_BASE = "/api";

export async function sendChatMessage(
  request: ChatRequest,
  signal?: AbortSignal
): Promise<Response> {
  return fetch(`${API_BASE}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(request),
    signal,
  });
}

export async function createSession(
  body?: SessionCreate
): Promise<SessionResponse> {
  const resp = await fetch(`${API_BASE}/sessions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });
  if (!resp.ok) throw new Error(`Failed to create session: ${resp.status}`);
  return resp.json();
}

export async function listSessions(): Promise<SessionResponse[]> {
  const resp = await fetch(`${API_BASE}/sessions`);
  if (!resp.ok) throw new Error(`Failed to list sessions: ${resp.status}`);
  return resp.json();
}

export async function getHealth(): Promise<HealthResponse> {
  const resp = await fetch(`${API_BASE}/health`);
  if (!resp.ok) throw new Error(`Failed to get health: ${resp.status}`);
  return resp.json();
}
