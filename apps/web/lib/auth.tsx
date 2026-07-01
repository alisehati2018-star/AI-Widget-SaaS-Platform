"use client";

// Client-side session management: login/signup/logout and a useSession() guard
// hook. Auth is carried entirely by httpOnly cookies issued by the backend
// (`vitrin_access` / `vitrin_refresh`) — no token ever touches localStorage or
// JS, so an XSS cannot steal the session. On a 401 the hook transparently
// rotates the refresh cookie once (the backend reads it from the cookie).
//
// The platform-admin plane is a fully separate identity (its own
// `admin_users`/`admin_sessions` tables, its own `/admin/auth/*` endpoints,
// its own cookie pair `vitrin_admin_access`/`vitrin_admin_refresh`/
// `vitrin_admin_csrf`) — see `adminLogin`/`adminFetch`/`useAdminSession` below.
// A customer session and an admin session can coexist in the same browser
// without either one reading or affecting the other.

import { useCallback, useEffect, useState } from "react";
import { apiFetch, ApiError, type SessionUser } from "./api";

interface TokenResponse {
  user: SessionUser;
}

const ADMIN_CSRF_COOKIE = "vitrin_admin_csrf";

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

// --------------------------------------------------------------------------- #
// Platform-admin plane — separate identity, separate cookies, separate API.   #
// --------------------------------------------------------------------------- #
export async function adminLogin(email: string, password: string): Promise<SessionUser> {
  const r = await apiFetch<TokenResponse>("/admin/auth/login", {
    body: { email, password },
    csrfCookie: ADMIN_CSRF_COOKIE,
  });
  return r.user;
}

export async function adminLogout(): Promise<void> {
  try {
    await apiFetch("/admin/auth/logout", { method: "POST", body: {}, csrfCookie: ADMIN_CSRF_COOKIE });
  } catch {
    // Best-effort, same rationale as logout() above.
  }
}

async function tryAdminRefresh(): Promise<boolean> {
  try {
    await apiFetch<TokenResponse>("/admin/auth/refresh", {
      method: "POST",
      body: {},
      csrfCookie: ADMIN_CSRF_COOKIE,
    });
    return true;
  } catch {
    return false;
  }
}

/** Admin-authenticated fetch with one transparent refresh-and-retry on 401.
 * Use this (not `authFetch`) for every call the admin panel makes, so an
 * expired access token rotates via the admin refresh cookie, not the
 * customer one. */
export async function adminFetch<T = unknown>(
  path: string,
  opts: { method?: string; body?: unknown } = {},
): Promise<T> {
  try {
    return await apiFetch<T>(path, { ...opts, csrfCookie: ADMIN_CSRF_COOKIE });
  } catch (e) {
    if (e instanceof ApiError && e.status === 401 && (await tryAdminRefresh())) {
      return apiFetch<T>(path, { ...opts, csrfCookie: ADMIN_CSRF_COOKIE });
    }
    throw e;
  }
}

/** Loads /admin/auth/me (via the admin-only cookie). */
export function useAdminSession(): SessionState & { reload: () => void } {
  const [state, setState] = useState<SessionState>({ user: null, loading: true });
  const reload = useCallback(() => {
    setState({ user: null, loading: true });
    adminFetch<SessionUser & { is_admin: boolean }>("/admin/auth/me")
      .then((u) => setState({ user: u, loading: false }))
      .catch(() => setState({ user: null, loading: false }));
  }, []);
  useEffect(() => reload(), [reload]);
  return { ...state, reload };
}
