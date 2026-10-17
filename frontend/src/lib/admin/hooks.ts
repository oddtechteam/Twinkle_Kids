"use client";

import { type Dispatch, type SetStateAction, useCallback, useEffect, useRef, useState } from "react";

import { useToast } from "@/components/ui/Toast";
import { ApiError } from "@/lib/api/client";

export interface Resource<T> {
  data: T | undefined;
  error: string | null;
  loading: boolean;
  reload: () => Promise<void>;
  setData: Dispatch<SetStateAction<T | undefined>>;
}

/** Loads data from the admin API; `loader` should be stable per key (pass the key to refetch). */
export function useResource<T>(loader: () => Promise<T>, key: string): Resource<T> {
  const [data, setData] = useState<T>();
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const loaderRef = useRef(loader);
  loaderRef.current = loader;

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      setData(await loaderRef.current());
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Something went wrong.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void reload();
  }, [key, reload]);

  return { data, error, loading, reload, setData };
}

/**
 * Runs a mutation, shows the backend's real outcome as a toast and reports success.
 * Nothing is shown as saved unless the API call actually succeeded.
 */
export function useMutation() {
  const toast = useToast();
  const [pending, setPending] = useState(false);

  const run = useCallback(
    async <T,>(action: () => Promise<T>, messages: { success?: string; error?: string } = {}) => {
      setPending(true);
      try {
        const result = await action();
        if (messages.success) toast.show({ title: messages.success });
        return { ok: true as const, result };
      } catch (e) {
        const detail = e instanceof ApiError || e instanceof Error ? e.message : "Unexpected error";
        toast.show({ tone: "warning", title: messages.error ?? "Couldn't save changes", description: detail });
        return { ok: false as const, error: detail };
      } finally {
        setPending(false);
      }
    },
    [toast],
  );

  return { run, pending };
}
