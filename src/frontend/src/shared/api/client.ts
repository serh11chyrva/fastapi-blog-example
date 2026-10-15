export type ApiRequestOptions = RequestInit;
export type ValidationIssue = {
  loc?: (string | number)[];
  msg: string;
  type?: string;
};
export class ApiError extends Error {
  constructor(message: string, public readonly status: number, public readonly details: unknown) {
    super(message);
    this.name = "ApiError";
  }
}
export function errorMessage(reason: unknown): string {
  return reason instanceof Error ? reason.message : "Something went wrong. Please try again.";
}
function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
export async function api<T>(path: string, init: ApiRequestOptions = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData))
    headers.set("Content-Type", "application/json");
  const response = await fetch(`/api/v1${path}`, { ...init, headers, credentials: "same-origin" });
  if (response.status === 204)
    return undefined as T;
  let payload: unknown;
  try {
    payload = await response.json();
  }
  catch {
    throw new ApiError("The server returned an unreadable response. Please try again.", response.status, null);
  }
  if (!response.ok) {
    const detail = isRecord(payload) ? payload.detail : undefined;
    const messages = Array.isArray(detail)
      ? detail.flatMap((issue: unknown) => isRecord(issue) && typeof issue.msg === "string" ? [issue.msg] : [])
      : [];
    const message = typeof detail === "string" ? detail : messages.join(" · ") || "Something went wrong. Please try again.";
    throw new ApiError(message, response.status, detail);
  }
  return payload as T;
}
