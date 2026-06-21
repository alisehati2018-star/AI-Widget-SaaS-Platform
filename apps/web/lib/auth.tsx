"use client";

// Client-side session management: token storage, login/signup/logout, and a
// useSession() guard hook. Access + refresh tokens live in localStorage; on a
// 401 the hook transparently rotates the refresh token once.

import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError, type SessionUser } from "./api";

const ACCESS = "vitrin.access";
const REFRESH = "vitrin.refresh";

export function getAccessToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(ACCESS);
}
function getRefreshToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem(REFRESH);
}
export function saveTokens(access: string, refresh: string): void {
  localStorage.setItem(ACCESS, access);
  localStorage.setItem(REFRESH, refresh);
}
export function clearTokens(): void {
  localStorage.removeItem(ACCESS);
  localStorage.removeItem(REFRESH);
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  user: SessionUser;
}

export async function login(email: string, password: string): Promise<SessionUser> {
  const r = await apiFetch<TokenResponse>("/auth/login", { body: { email, password } });
  saveTokens(r.access_token, r.refresh_token);
  return r.user;
}

export async function signup(input: {
  email: string;
  password: string;
  store_name: string;
  full_name?: string;
}): Promise<SessionUser> {
  const r = await apiFetch<TokenResponse>("/auth/signup", { body: input });
  saveTokens(r.access_token, r.refresh_token);
  return r.user;
}

export async function logout(): Promise<void> {
  const refresh = getRefreshToken();
  try {
    if (refresh) await apiFetch("/auth/logout", { body: { refresh_token: refresh } });
  } finally {
    clearTokens();
  }
}

async function tryRefresh(): Promise<boolean> {
  const refresh = getRefreshToken();
  if (!refresh) return false;
  try {
    const r = await apiFetch<TokenResponse>("/auth/refresh", { body: { refresh_token: refresh } });
    saveTokens(r.access_token, r.refresh_token);
    return true;
  } catch {
    clearTokens();
    return false;
  }
}

/** Authenticated fetch with one transparent refresh-and-retry on 401. */
export async function authFetch<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  try {
    return await apiFetch<T>(path, { ...opts, token: getAccessToken() });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && (await tryRefresh())) {
      return apiFetch<T>(path, { ...opts, token: getAccessToken() });
    }
    throw e;
  }
}

export interface SessionState {
  user: SessionUser | null;
  loading: boolean;
}

/** Loads /auth/me. Pass a required role to guard a surface. */
export function useSession(): SessionState & { reload: () => void } {
  const [state, setState] = useState<SessionState>({ user: null, loading: true });
  const reload = useCallback(() => {
    setState({ user: null, loading: true });
    if (!getAccessToken()) {
      setState({ user: null, loading: false });
      return;
    }
    authFetch<SessionUser & { is_admin: boolean }>("/auth/me")
      .then((u) => setState({ user: u, loading: false }))
      .catch(() => setState({ user: null, loading: false }));
  }, []);
  useEffect(() => reload(), [reload]);
  return { ...state, reload };
}
