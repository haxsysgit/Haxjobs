import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

export function SetupPage() {
  return (
    <div className="space-y-6">
      <h2 className="text-2xl font-heading font-bold tracking-tight">Setup</h2>
      <Card>
        <CardHeader>
          <CardTitle>Provider Configuration</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-muted-foreground">
            Configure your LLM provider and API key. Full setup wizard coming in
            the next update.
          </p>
        </CardContent>
      </Card>
    </div>
  )
}
