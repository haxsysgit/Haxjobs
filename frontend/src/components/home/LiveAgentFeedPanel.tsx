import { AgentActivityFeed } from "@/components/app/AgentActivityFeed"

interface LiveAgentFeedPanelProps {
  eventCount: number
}

export function LiveAgentFeedPanel({ eventCount }: LiveAgentFeedPanelProps) {
  return (
    <div className="flex max-h-[calc(100vh-7rem)] flex-col overflow-hidden rounded-3xl border bg-card shadow-sm">
      <div className="flex items-center justify-between border-b px-4 py-3">
        <div className="flex items-center gap-2">
          <span className="relative flex size-2.5">
            <span className="absolute inline-flex size-full animate-ping rounded-full bg-primary opacity-60" />
            <span className="relative inline-flex size-2.5 rounded-full bg-primary" />
          </span>
          <h2 className="font-heading text-lg">Live Feed</h2>
        </div>
        <span className="rounded-full border bg-background px-2.5 py-1 text-xs text-muted-foreground">
          {eventCount} events
        </span>
      </div>
      <div className="min-h-0 flex-1 overflow-y-auto p-3">
        <AgentActivityFeed variant="compact" maxEvents={12} hideHeader />
      </div>
    </div>
  )
}
