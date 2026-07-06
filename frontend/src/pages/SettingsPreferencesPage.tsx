import type { ReactNode } from "react"
import { MapPin, SlidersHorizontal, Target, Waves } from "lucide-react"
import { PageHeader } from "@/components/app/PageHeader"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"

function PreferenceRow({ icon, label, value, note }: { icon: ReactNode; label: string; value: string; note: string }) {
  return (
    <div className="flex gap-3 rounded-2xl border bg-background/70 p-4">
      <div className="grid size-9 shrink-0 place-items-center rounded-xl bg-primary/10 text-primary">
        {icon}
      </div>
      <div>
        <p className="text-sm font-medium">{label}</p>
        <p className="mt-1 font-heading text-xl">{value}</p>
        <p className="mt-1 text-xs text-muted-foreground">{note}</p>
      </div>
    </div>
  )
}

export function SettingsPreferencesPage() {
  return (
    <div className="space-y-6">
      <PageHeader title="Preferences" kicker="Control Room" description="Read-only defaults until profile editing lands." />
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 font-heading text-2xl">
            <SlidersHorizontal className="size-5 text-primary" />
            Current hunt defaults
          </CardTitle>
        </CardHeader>
        <CardContent className="grid gap-3 lg:grid-cols-2">
          <PreferenceRow
            icon={<MapPin className="size-4" />}
            label="Search radius"
            value="London + Remote"
            note="Used as a preview of the default location posture."
          />
          <PreferenceRow
            icon={<Waves className="size-4" />}
            label="Profile depth"
            value="Lenient"
            note="Ask for useful evidence without turning onboarding into homework."
          />
          <PreferenceRow
            icon={<Target className="size-4" />}
            label="Minimum score"
            value="55%"
            note="Below this, jobs stay out of the main arena unless requested."
          />
          <PreferenceRow
            icon={<SlidersHorizontal className="size-4" />}
            label="Work modes"
            value="Remote, hybrid, onsite"
            note="Final filtering still comes from the canonical profile."
          />
        </CardContent>
      </Card>
      <p className="text-xs text-muted-foreground">
        These are preview rows. They do not write profile data or change backend settings yet.
      </p>
    </div>
  )
}
