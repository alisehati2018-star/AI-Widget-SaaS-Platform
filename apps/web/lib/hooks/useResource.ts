"use client";

// Shared data-fetching hook — replaces the repeated
// `useState + useEffect + authFetch + .catch` triplet across pages.
// Returns the loaded value, loading/error state, and a reload() for mutations.

import { useCallback, useEffect, useState } from "react";
import { adminFetch, authFetch } from "@/lib/auth";

export interface Resource<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

function makeResourceHook(fetcher: typeof authFetch) {
  return function useResourceImpl<T>(path: string | null): Resource<T> {
    const [data, setData] = useState<T | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const reload = useCallback(() => {
      if (!path) {
        setLoading(false);
        return;
      }
      setLoading(true);
      fetcher<T>(path)
        .then((d) => {
          setData(d);
          setError(null);
        })
        .catch((e) => setError(e instanceof Error ? e.message : String(e)))
        .finally(() => setLoading(false));
    }, [path]);

    useEffect(() => reload(), [reload]);

    return { data, loading, error, reload };
  };
}

/** For the owner/customer dashboard — retries via the customer refresh cookie. */
export const useResource = makeResourceHook(authFetch);

/** For the admin panel — retries via the admin-only refresh cookie, so an
 * expired admin access token never gets rotated through the customer plane. */
export const useAdminResource = makeResourceHook(adminFetch);
