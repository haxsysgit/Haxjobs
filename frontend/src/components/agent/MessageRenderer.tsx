"use client";

import { MessageShell } from "./MessageShell";
import {
  EvaluationCard,
  DiscoveryCard,
  PackCard,
  DecisionCard,
  AlertCard,
  TextCard,
  CompareCard,
} from "./cards";
import { useAgentActions } from "./context";
import type { MessageView, JobView } from "../../lib/opusTypes";

export function MessageRenderer({ message }: { message: MessageView }) {
  const { jobBySlug } = useAgentActions();
  const active =
    message.kind === "discovery" && (message.payload.status as string) === "sweeping";

  if (message.author === "user") {
    return (
      <MessageShell author="user" createdAt={message.createdAt}>
        {(message.payload.text as string) ?? ""}
      </MessageShell>
    );
  }

  return (
    <MessageShell
      author="hax"
      createdAt={message.createdAt}
      active={active}
      showFeedback={message.kind !== "decision"}
    >
      {renderCard(message, jobBySlug)}
    </MessageShell>
  );
}

function renderCard(
  message: MessageView,
  jobBySlug: (slug: string) => JobView | undefined,
) {
  switch (message.kind) {
    case "evaluation": {
      const job = jobBySlug(message.payload.jobSlug as string);
      if (!job) return <TextCard payload={{ text: "Job not found." }} />;
      return <EvaluationCard job={job} />;
    }
    case "discovery":
      return <DiscoveryCard payload={message.payload} />;
    case "pack":
      return <PackCard payload={message.payload} />;
    case "decision":
      return <DecisionCard payload={message.payload} />;
    case "alert":
      return <AlertCard payload={message.payload} />;
    case "compare":
      return <CompareCard payload={message.payload} />;
    default:
      return <TextCard payload={message.payload} />;
  }
}
