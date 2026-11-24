import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, assess, getDues, getHistory, getLifeEvents } from "./api";
import type { Snapshot } from "./types";

export function useLatestSnapshot(userId: string | null) {
  return useQuery({
    queryKey: ["latest", userId],
    enabled: Boolean(userId),
    queryFn: async (): Promise<Snapshot | null> => {
      try {
        return (await getHistory(userId!, 1)).snapshots[0] ?? null;
      } catch (err) {
        if (err instanceof ApiError && err.status === 404) return null;
        throw err;
      }
    },
  });
}

export function useReassess(userId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => assess(userId!),
    onSuccess: (snapshot) => {
      queryClient.setQueryData(["latest", userId], snapshot);
      void queryClient.invalidateQueries({ queryKey: ["history", userId] });
      void queryClient.invalidateQueries({ queryKey: ["notifications", userId] });
    },
  });
}

/** Refresh every view that depends on the twin's inputs after a life event changes them. */
export function useRefreshTwin(userId: string | null) {
  const queryClient = useQueryClient();
  return () => {
    for (const key of ["latest", "history", "inputs", "notifications", "life-events", "dues"]) {
      void queryClient.invalidateQueries({ queryKey: [key, userId] });
    }
    void queryClient.invalidateQueries({ queryKey: ["whatif"] });
    void queryClient.invalidateQueries({ queryKey: ["simulate"] });
  };
}

export function useDues(userId: string | null) {
  return useQuery({
    queryKey: ["dues", userId],
    queryFn: () => getDues(userId!),
    enabled: Boolean(userId),
  });
}

export function useLifeEvents(userId: string | null) {
  return useQuery({
    queryKey: ["life-events", userId],
    queryFn: () => getLifeEvents(userId!),
    enabled: Boolean(userId),
  });
}
