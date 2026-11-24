import { Component, lazy, Suspense, type ReactNode } from "react";

const HoloTwin = lazy(() => import("./HoloTwin"));

function supportsWebGL(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return Boolean(canvas.getContext("webgl2") ?? canvas.getContext("webgl"));
  } catch {
    return false;
  }
}

class ErrorBoundary extends Component<{ fallback: ReactNode; children: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? this.props.fallback : this.props.children;
  }
}

/** Renders the 3D hologram when WebGL works, otherwise the given 2D fallback. */
export function TwinVisual({ risk, fallback }: { risk?: number; fallback: ReactNode }) {
  if (!supportsWebGL()) return <>{fallback}</>;
  return (
    <ErrorBoundary fallback={fallback}>
      <Suspense fallback={fallback}>
        <HoloTwin risk={risk} />
      </Suspense>
    </ErrorBoundary>
  );
}
