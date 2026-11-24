import { useSyncExternalStore } from "react";

const KEY = "twinlife-motion";
const listeners = new Set<() => void>();

/** True when the user forced full motion in-app, overriding the OS reduced-motion setting. */
export function isFullMotion(): boolean {
  return localStorage.getItem(KEY) === "full";
}

export function setFullMotion(full: boolean) {
  localStorage.setItem(KEY, full ? "full" : "system");
  document.documentElement.dataset.motion = full ? "full" : "system";
  listeners.forEach((notify) => notify());
}

export function initMotionPreference() {
  document.documentElement.dataset.motion = isFullMotion() ? "full" : "system";
}

export function useFullMotion(): boolean {
  return useSyncExternalStore(
    (notify) => {
      listeners.add(notify);
      return () => listeners.delete(notify);
    },
    isFullMotion,
  );
}

export function prefersReducedMotion(): boolean {
  return !isFullMotion() && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}
