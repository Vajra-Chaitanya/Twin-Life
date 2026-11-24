import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { getNotifications, markNotificationsRead } from "./api";

export function useNotifications(userId: string | null) {
  return useQuery({
    queryKey: ["notifications", userId],
    queryFn: () => getNotifications(userId!),
    enabled: Boolean(userId),
    refetchInterval: 15_000,
  });
}

export function useMarkRead(userId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (ids?: number[]) => markNotificationsRead(userId!, ids),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications", userId] }),
  });
}
