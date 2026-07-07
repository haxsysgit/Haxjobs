import { useParams } from "react-router-dom"
import { WorkspaceClient } from "@/components/workspace/WorkspaceClient"
import { getJobs, getMessages, getStats } from "@/lib/fixtures"

export default function WorkspacePage() {
  const { roleId } = useParams<{ roleId?: string }>()
  const messages = getMessages()
  const jobs = getJobs()
  const stats = getStats()
  return (
    <WorkspaceClient
      initialMessages={messages}
      initialJobs={jobs}
      initialStats={stats}
      trackFilter={roleId}
    />
  )
}
