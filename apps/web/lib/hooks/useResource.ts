"use client";

// Shared data-fetching hook — replaces the repeated
// `useState + useEffect + authFetch + .catch` triplet across pages.
// Returns the loaded value, loading/error state, and a reload() for mutations.

import { useCallback, useEffect, useState } from "react";
import { authFetch } from "@/lib/auth";

export interface Resource<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

export function useResource<T>(path: string | null): Resource<T> {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(() => {
    if (!path) {
      setLoading(false);
      return;
    }
    setLoading(true);
    authFetch<T>(path)
      .then((d) => {
        setData(d);
        setError(null);
      })
      .catch((e) => setError(e instanceof Error ? e.message : String(e)))
      .finally(() => setLoading(false));
  }, [path]);

  useEffect(() => reload(), [reload]);

  return { data, loading, error, reload };
}
