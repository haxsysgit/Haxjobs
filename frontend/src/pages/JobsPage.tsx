import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function JobsPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-bold tracking-tight">Jobs</h2>
      <Card>
        <CardHeader>
          <CardTitle>Coming Soon</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Job listings and evaluations will appear here.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
