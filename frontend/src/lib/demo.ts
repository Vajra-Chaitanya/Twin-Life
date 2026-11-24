import type { QueryClient } from "@tanstack/react-query";
import { assess, onboard } from "./api";
import { PERSONAS, type Persona } from "./personas";
import { setCurrentUser } from "./user";

export async function loadPersona(persona: Persona, queryClient: QueryClient) {
  await onboard(persona.payload);
  const snapshot = await assess(persona.payload.user_id);
  setCurrentUser(persona.payload.user_id);
  queryClient.setQueryData(["latest", persona.payload.user_id], snapshot);
  await queryClient.invalidateQueries();
  return snapshot;
}

/** Calibrate every demo persona, ending on the high-risk one for the most dramatic dashboard. */
export async function seedDemo(queryClient: QueryClient) {
  const ordered = [...PERSONAS.filter((p) => p.key !== "rahul"), ...PERSONAS.filter((p) => p.key === "rahul")];
  for (const persona of ordered) await loadPersona(persona, queryClient);
}
