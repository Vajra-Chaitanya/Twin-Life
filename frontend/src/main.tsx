import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MotionConfig } from "framer-motion";
import App from "./App";
import { initMotionPreference, useFullMotion } from "./lib/motion";
import "./index.css";

initMotionPreference();

function Root() {
  const fullMotion = useFullMotion();
  return (
    <MotionConfig reducedMotion={fullMotion ? "never" : "user"}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </MotionConfig>
  );
}

const queryClient = new QueryClient({
  defaultOptions: { queries: { refetchOnWindowFocus: false } },
});

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <Root />
    </QueryClientProvider>
  </StrictMode>,
);
