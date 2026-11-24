import { useSyncExternalStore } from "react";

const KEY = "twinlife-user";
const listeners = new Set<() => void>();

export const getCurrentUser = () => localStorage.getItem(KEY);

export function setCurrentUser(userId: string) {
  localStorage.setItem(KEY, userId);
  listeners.forEach((notify) => notify());
}

export function useCurrentUser(): string | null {
  return useSyncExternalStore((notify) => {
    listeners.add(notify);
    return () => listeners.delete(notify);
  }, getCurrentUser);
}
