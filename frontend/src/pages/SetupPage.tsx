import { useState, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group"
import { Badge } from "@/components/ui/badge"

type Preset = { key: string; name: string; models: string[] }
type Status = { configured: boolean; provider: string | null; presets: Preset[] }

export function SetupPage() {
  const navigate = useNavigate()
  const [status, setStatus] = useState<Status | null>(null)
  const [provider, setProvider] = useState("deepseek")
  const [apiKey, setApiKey] = useState("")
  const [model, setModel] = useState("")
  const [baseUrl, setBaseUrl] = useState("")
  const [showKey, setShowKey] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState("")

  useEffect(() => {
    fetch("/api/setup/status")
      .then((r) => r.json())
      .then((data: Status) => {
        setStatus(data)
        if (data.configured) return
        const preset = data.presets.find((p) => p.key === "deepseek")
        if (preset) setModel(preset.models[0])
      })
  }, [])

  const selectedPreset = status?.presets.find((p) => p.key === provider)
  const isCustom = provider === "custom"

  function handleProviderChange(key: string) {
    setProvider(key)
    const preset = status?.presets.find((p) => p.key === key)
    if (preset && !isCustom) {
      setModel(preset.models[0])
    }
  }

  async function handleConnect() {
    if (!apiKey.trim()) {
      setError("API key is required")
      return
    }
    setSaving(true)
    setError("")
    try {
      const body: Record<string, string> = { provider, api_key: apiKey, model }
      if (isCustom) body.base_url = baseUrl
      const res = await fetch("/api/setup/configure", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      })
      if (!res.ok) throw new Error("Failed to save config")
      navigate("/")
    } catch {
      setError("Failed to save configuration")
    } finally {
      setSaving(false)
    }
  }

  if (!status) return null

  if (status.configured) {
    return (
      <div className="space-y-6">
        <h2 className="text-2xl font-heading font-bold tracking-tight">Setup</h2>
        <Card>
          <CardHeader>
            <CardTitle>✓ Provider Configured</CardTitle>
            <CardDescription>
              Your {status.provider} provider is ready. You can reconfigure below
              or manage your API key in <code>~/.haxjobs/config.toml</code>.
            </CardDescription>
          </CardHeader>
        </Card>
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <h2 className="text-2xl font-heading font-bold tracking-tight">Setup</h2>

      <Card>
        <CardHeader>
          <CardTitle>Choose your LLM provider</CardTitle>
          <CardDescription>
            HaxJobs needs an API key to run evaluations, generate packs, and
            power the agent pipeline.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Provider selector */}
          <div className="space-y-2">
            <Label>Provider</Label>
            <RadioGroup value={provider} onValueChange={handleProviderChange}>
              {status.presets.map((p) => (
                <label
                  key={p.key}
                  className={`flex items-center gap-3 rounded-lg border p-4 cursor-pointer transition-colors ${
                    provider === p.key
                      ? "border-primary bg-primary/5"
                      : "hover:bg-muted/50"
                  }`}
                >
                  <RadioGroupItem value={p.key} />
                  <div className="flex-1">
                    <div className="font-medium">{p.name}</div>
                    <div className="text-sm text-muted-foreground">
                      {p.key !== "custom"
                        ? p.models.join(", ")
                        : "Set your own endpoint"}
                    </div>
                  </div>
                  {p.key === "deepseek" && (
                    <Badge variant="secondary">Default</Badge>
                  )}
                </label>
              ))}
            </RadioGroup>
          </div>

          {/* Custom provider fields */}
          {isCustom && (
            <div className="space-y-3 pl-7 border-l-2 border-muted">
              <div className="space-y-1">
                <Label htmlFor="base-url">Base URL</Label>
                <Input
                  id="base-url"
                  placeholder="https://api.example.com/v1"
                  value={baseUrl}
                  onChange={(e) => setBaseUrl(e.target.value)}
                />
              </div>
              <div className="space-y-1">
                <Label htmlFor="custom-model">Model</Label>
                <Input
                  id="custom-model"
                  placeholder="your-model-name"
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                />
              </div>
            </div>
          )}

          {/* Model selector (non-custom) */}
          {!isCustom && selectedPreset && (
            <div className="space-y-1">
              <Label htmlFor="model">Model</Label>
              <select
                id="model"
                className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-sm transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
                value={model}
                onChange={(e) => setModel(e.target.value)}
              >
                {selectedPreset.models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* API key */}
          <div className="space-y-1">
            <Label htmlFor="api-key">API Key</Label>
            <div className="relative">
              <Input
                id="api-key"
                type={showKey ? "text" : "password"}
                placeholder="sk-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
              <button
                type="button"
                onClick={() => setShowKey(!showKey)}
                className="absolute right-2 top-1/2 -translate-y-1/2 text-xs text-muted-foreground hover:text-foreground"
              >
                {showKey ? "Hide" : "Show"}
              </button>
            </div>
          </div>

          {error && (
            <p className="text-sm text-destructive">{error}</p>
          )}

          <Button
            onClick={handleConnect}
            disabled={saving || !apiKey.trim()}
            className="w-full"
          >
            {saving ? "Connecting..." : "Connect"}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
