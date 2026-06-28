"use client";

// Client-side session management: login/signup/logout and a useSession() guard
// hook. Auth is carried entirely by httpOnly cookies issued by the backend
// (`vitrin_access` / `vitrin_refresh`) — no token ever touches localStorage or
// JS, so an XSS cannot steal the session. On a 401 the hook transparently
// rotates the refresh cookie once (the backend reads it from the cookie).

import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError, type SessionUser } from "./api";

interface TokenResponse {
  user: SessionUser;
}

export async function login(email: string, password: string): Promise<SessionUser> {
  // Backend sets the auth cookies on the response; we only need the user.
  const r = await apiFetch<TokenResponse>("/auth/login", { body: { email, password } });
  return r.user;
}

export async function signup(input: {
  email: string;
  password: string;
  store_name: string;
  full_name?: string;
}): Promise<SessionUser> {
  const r = await apiFetch<TokenResponse>("/auth/signup", { body: input });
  return r.user;
}

export async function logout(): Promise<void> {
  // The refresh token rides in the httpOnly cookie; the backend revokes the
  // session and clears all auth cookies. Body is empty but the route is POST.
  try {
    await apiFetch("/auth/logout", { method: "POST", body: {} });
  } catch {
    // Best-effort: even if revocation fails, the cookies are cleared below by
    // the server on the next successful call; nothing is kept client-side.
  }
}

async function tryRefresh(): Promise<boolean> {
  try {
    // Refresh token is read from the httpOnly cookie by the backend.
    await apiFetch<TokenResponse>("/auth/refresh", { method: "POST", body: {} });
    return true;
  } catch {
    return false;
  }
}

/** Authenticated fetch with one transparent refresh-and-retry on 401. */
export async function authFetch<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  try {
    return await apiFetch<T>(path, opts);
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && (await tryRefresh())) {
      return apiFetch<T>(path, opts);
    }
    throw e;
  }
}

export interface SessionState {
  user: SessionUser | null;
  loading: boolean;
}

/** Loads /auth/me (via the auth cookie). Pass a required role to guard a surface. */
export function useSession(): SessionState & { reload: () => void } {
  const [state, setState] = useState<SessionState>({ user: null, loading: true });
  const reload = useCallback(() => {
    setState({ user: null, loading: true });
    authFetch<SessionUser & { is_admin: boolean }>("/auth/me")
      .then((u) => setState({ user: u, loading: false }))
      .catch(() => setState({ user: null, loading: false }));
  }, []);
  useEffect(() => reload(), [reload]);
  return { ...state, reload };
}
