"use client";

import { createContext, useContext } from "react";
import type { JobView } from "../../lib/opusTypes"

export interface AgentActions {
  jobs: JobView[];
  jobBySlug: (slug: string) => JobView | undefined;
  decide: (job: JobView, decision: string, reason: string | null) => void;
  runRecon: (target?: string) => void;
  buildPack: (job: JobView) => void;
  trigger: (text: string) => void;
  compare: (slugs: string[]) => void;
  busy: boolean;
}

export const AgentActionsContext = createContext<AgentActions | null>(null);

export function useAgentActions(): AgentActions {
  const ctx = useContext(AgentActionsContext);
  if (!ctx) throw new Error("useAgentActions must be used within provider");
  return ctx;
}
