let done = false;
const listeners = new Set<() => void>();

export function isSplashDone() {
  return done;
}

export function markSplashDone() {
  if (done) return;
  done = true;
  listeners.forEach((notify) => notify());
  listeners.clear();
}

/** Runs once the startup splash starts leaving (immediately if it already has). */
export function onSplashDone(callback: () => void): () => void {
  if (done) {
    callback();
    return () => {};
  }
  listeners.add(callback);
  return () => listeners.delete(callback);
}
