import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, assess, getHistory } from "./api";
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
