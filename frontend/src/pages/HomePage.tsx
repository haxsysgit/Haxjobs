import { DashboardClient } from "@/components/dashboard/DashboardClient"
import { getJobs, getStats, getMemory, getMessages } from "@/lib/fixtures"

export default function HomePage() {
  const jobs = getJobs()
  const stats = getStats()
  const memory = getMemory()
  const messages = getMessages()
  const recent = messages.slice(-5).reverse()
  return <DashboardClient jobs={jobs} stats={stats} memory={memory} recent={recent} />
}
