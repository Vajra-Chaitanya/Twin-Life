import type {
  AdviceSimulationResponse,
  ChatMessage,
  ChatThread,
  Commitment,
  Due,
  LifeEvent,
  Notification,
  OnboardPayload,
  SimulateRequest,
  SimulateResponse,
  Snapshot,
  Twin,
  WhatIfResponse,
} from "./types";

export type HealthStatus = { status: string };

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // Non-JSON error body; keep the status text.
    }
    throw new ApiError(response.status, detail);
  }
  return response.json() as Promise<T>;
}

export const getHealth = () => apiFetch<HealthStatus>("/health");

export const onboard = (payload: OnboardPayload) =>
  apiFetch<{ user_id: string; status: "created" | "updated" }>("/onboard", {
    method: "POST",
    body: JSON.stringify(payload),
  });

export const assess = (userId: string) =>
  apiFetch<Snapshot>("/assess", { method: "POST", body: JSON.stringify({ user_id: userId }) });

export const getHistory = (userId: string, limit = 20) =>
  apiFetch<{ user_id: string; snapshots: Snapshot[] }>(
    `/history?${new URLSearchParams({ user_id: userId, limit: String(limit) })}`,
  );

export const askAdvisor = (userId: string, query: string, threadId: string, domain?: Twin) =>
  apiFetch<ChatMessage>("/query", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, query, thread_id: threadId, ...(domain ? { domain } : {}) }),
  });

export const getChatHistory = (userId: string, threadId: string, domain?: Twin) =>
  apiFetch<{ user_id: string; threads: ChatThread[]; messages: ChatMessage[] }>(
    `/chat-history?${new URLSearchParams({ user_id: userId, thread_id: threadId, ...(domain ? { domain } : {}) })}`,
  );

export const renameThread = (userId: string, threadId: string, title: string) =>
  apiFetch<{ thread_id: string; title: string }>(`/chat-threads/${encodeURIComponent(threadId)}`, {
    method: "PATCH",
    body: JSON.stringify({ user_id: userId, title }),
  });

export const deleteThread = (userId: string, threadId: string) =>
  apiFetch<{ thread_id: string; deleted_messages: number }>(
    `/chat-threads/${encodeURIComponent(threadId)}?${new URLSearchParams({ user_id: userId })}`,
    { method: "DELETE" },
  );

export const getDues = (userId: string) =>
  apiFetch<{ user_id: string; dues: Due[]; attention: number }>(`/dues?${new URLSearchParams({ user_id: userId })}`);

export const getNotifications = (userId: string) =>
  apiFetch<{ user_id: string; unread: number; notifications: Notification[] }>(
    `/notifications?${new URLSearchParams({ user_id: userId, limit: "100" })}`,
  );

export const markNotificationsRead = (userId: string, ids?: number[]) =>
  apiFetch<{ updated: number }>("/notifications/read", {
    method: "POST",
    body: JSON.stringify(ids ? { user_id: userId, ids } : { user_id: userId }),
  });

export const getInputs = (userId: string) =>
  apiFetch<OnboardPayload>(`/inputs?${new URLSearchParams({ user_id: userId })}`);

export const getLifeEvents = (userId: string) =>
  apiFetch<{ user_id: string; events: LifeEvent[]; counts: Record<Twin, number>; commitments: Commitment[] }>(
    `/events?${new URLSearchParams({ user_id: userId })}`,
  );

export const simulate = (request: SimulateRequest) =>
  apiFetch<SimulateResponse>("/simulate", { method: "POST", body: JSON.stringify(request) });

export const simulateAdvice = (userId: string, advice: string) =>
  apiFetch<AdviceSimulationResponse>("/simulate-advice", { method: "POST", body: JSON.stringify({ user_id: userId, advice }) });

export const whatIf = (userId: string, purchaseCost: number) =>
  apiFetch<WhatIfResponse>("/whatif", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, purchase_cost: purchaseCost }),
  });
