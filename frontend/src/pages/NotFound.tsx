import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 text-center">
      <p className="font-display text-7xl font-bold text-metal">404</p>
      <p className="text-taupe">This timeline doesn't exist.</p>
      <Link to="/" className="btn-ghost">Return home</Link>
    </div>
  );
}
