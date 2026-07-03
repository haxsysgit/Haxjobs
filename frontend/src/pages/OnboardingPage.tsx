import { useCallback, useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { AnimatePresence, motion } from "framer-motion"
import { toast } from "sonner"
import { ArrowLeft, Check, Circle, File, FileText, Sparkles, Upload, X } from "lucide-react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Spinner } from "@/components/ui/spinner"
import { Textarea } from "@/components/ui/textarea"

type Step = "welcome" | "source" | "upload" | "paste" | "extracting" | "review" | "complete"
type Source = "upload" | "paste"
type SectionStatus = "complete" | "review" | "missing"

interface ExtractionPhase {
  phase: string
  label: string
  done: boolean
}

interface FieldQuestion {
  field: string
  question: string
  type: string
  description: string
  current_value?: string | string[] | null
}

interface ExtractResponse {
  profile: Record<string, unknown>
  next_question: FieldQuestion | null
  questions_remaining: number
  phase: string
  extraction_phases: ExtractionPhase[]
}

interface ReviewSection {
  key: string
  title: string
  status: SectionStatus
  summary: string
  details: string[]
}

const API = "/api"
const MIN_CV_CHARS = 100
const MAX_FILE_BYTES = 5 * 1024 * 1024

const stepVariants = {
  enter: { opacity: 0, y: 18 },
  center: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -18 },
}

const FLOW_STEPS = ["Start", "Source", "Extract", "Review"]
const DEFAULT_PHASES = [
  "Reading your CV",
  "Extracting profile facts",
  "Organizing skills and experience",
  "Asking the agent to enrich the profile",
  "Preparing review",
]

async function uploadCV(file: File): Promise<ExtractResponse> {
  const form = new FormData()
  form.append("file", file)
  const response = await fetch(`${API}/onboarding/upload`, { method: "POST", body: form })
  if (!response.ok) throw new Error(await errorMessage(response, "Upload failed"))
  return response.json()
}

async function extractText(text: string): Promise<ExtractResponse> {
  const response = await fetch(`${API}/onboarding/extract-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  })
  if (!response.ok) throw new Error(await errorMessage(response, "Extraction failed"))
  return response.json()
}

async function submitAnswer(questionId: string, answer: string): Promise<{
  profile: Record<string, unknown>
  next_question: FieldQuestion | null
  questions_remaining: number
  phase: string
}> {
  const response = await fetch(`${API}/onboarding/wizard`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer }),
  })
  if (!response.ok) throw new Error(await errorMessage(response, "Could not save that answer"))
  return response.json()
}

async function completeOnboarding() {
  const response = await fetch(`${API}/onboarding/complete`, { method: "POST" })
  if (!response.ok) throw new Error(await errorMessage(response, "Could not save your profile"))
  return response.json()
}

async function errorMessage(response: Response, fallback: string) {
  const body = await response.json().catch(() => null)
  return typeof body?.detail === "string" ? body.detail : fallback
}

function MotionStep({ children, className = "" }: { children: React.ReactNode; className?: string }) {
  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className={className}>
      {children}
    </motion.div>
  )
}

function WizardProgress({ active }: { active: number }) {
  return (
    <div className="mb-8">
      <div className="grid grid-cols-4 gap-2">
        {FLOW_STEPS.map((label, index) => {
          const done = index < active
          const current = index === active
          return (
            <div key={label} className="space-y-2">
              <div className={`h-1.5 rounded-full transition-all ${done || current ? "bg-primary" : "bg-muted"}`} />
              <p className={`text-[11px] ${done || current ? "text-foreground" : "text-muted-foreground"}`}>
                {label}
              </p>
            </div>
          )
        })}
      </div>
    </div>
  )
}

function BackButton({ onClick }: { onClick: () => void }) {
  return (
    <Button variant="ghost" size="sm" onClick={onClick} className="mb-5 -ml-2 text-muted-foreground">
      <ArrowLeft className="mr-1 size-4" />
      Back
    </Button>
  )
}

function statusBadge(status: SectionStatus) {
  if (status === "complete") return <Badge className="bg-primary/10 text-primary hover:bg-primary/10">Complete</Badge>
  if (status === "review") return <Badge variant="secondary">Needs review</Badge>
  return <Badge variant="outline" className="border-amber-500/40 text-amber-600">Missing</Badge>
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <MotionStep className="mx-auto max-w-3xl">
      <div className="grid gap-8 lg:grid-cols-[1fr_0.9fr] lg:items-center">
        <div className="space-y-5">
          <Badge variant="secondary" className="gap-1 rounded-full px-3 py-1">
            <Sparkles className="size-3" />
            Profile first, jobs second
          </Badge>
          <div className="space-y-3">
            <h1 className="text-4xl font-heading tracking-tight sm:text-5xl">Let&apos;s build your hiring profile</h1>
            <p className="max-w-xl text-base leading-7 text-muted-foreground">
              We will turn your CV into a structured profile. HaxJobs uses it to understand your skills,
              experience, goals, strengths, gaps, and what kind of work actually fits you.
            </p>
          </div>
          <Button size="lg" onClick={onNext} className="min-w-44">
            Get started
          </Button>
        </div>

        <Card className="border-primary/15 bg-muted/20 shadow-sm">
          <CardHeader>
            <CardTitle className="font-heading text-xl">What happens next</CardTitle>
            <CardDescription>No busywork. The CV does the heavy lifting.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            {[
              ["Upload or paste", "Start with your CV, PDF, DOCX, Markdown, or plain text."],
              ["Extract and enrich", "Deterministic parsing fills the basics. The agent adds structure and depth."],
              ["Review and confirm", "You see the profile before saving. Your edits win."],
              ["Then HaxJobs can work", "Discovery, evaluation, tailoring, and learning all use this profile."],
            ].map(([title, body], index) => (
              <div key={title} className="flex gap-3">
                <div className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
                  {index + 1}
                </div>
                <div>
                  <p className="font-medium">{title}</p>
                  <p className="text-muted-foreground">{body}</p>
                </div>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </MotionStep>
  )
}

function SourceStep({ onSelect }: { onSelect: (source: Source) => void }) {
  return (
    <MotionStep className="mx-auto max-w-3xl">
      <WizardProgress active={1} />
      <div className="mb-7 text-center">
        <h2 className="text-3xl font-heading tracking-tight">Choose your starting point</h2>
        <p className="mt-2 text-muted-foreground">Pick the easiest way to give HaxJobs your CV. We will do the rest.</p>
      </div>
      <div className="grid gap-4 sm:grid-cols-2">
        <button
          type="button"
          onClick={() => onSelect("upload")}
          className="group rounded-2xl border bg-card p-6 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
        >
          <div className="mb-5 flex items-center justify-between">
            <div className="rounded-2xl bg-primary/10 p-3 text-primary">
              <Upload className="size-6" />
            </div>
            <Badge variant="secondary">Recommended</Badge>
          </div>
          <h3 className="text-lg font-semibold">Upload a file</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Best if your CV is ready as PDF, DOCX, Markdown, or text.
          </p>
        </button>

        <button
          type="button"
          onClick={() => onSelect("paste")}
          className="group rounded-2xl border bg-card p-6 text-left shadow-sm transition-all hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-md"
        >
          <div className="mb-5 rounded-2xl bg-primary/10 p-3 text-primary w-fit">
            <FileText className="size-6" />
          </div>
          <h3 className="text-lg font-semibold">Paste CV text</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            Good when you want to copy from a document or make a quick test run.
          </p>
        </button>
      </div>
    </MotionStep>
  )
}

function UploadStep({
  file,
  onBack,
  onChoose,
  onClear,
  onContinue,
  isSubmitting,
}: {
  file: File | null
  onBack: () => void
  onChoose: (file: File) => void
  onClear: () => void
  onContinue: () => void
  isSubmitting: boolean
}) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const chooseFile = useCallback((nextFile: File) => {
    if (nextFile.size > MAX_FILE_BYTES) {
      toast.error("That file is too large. Max 5 MB.")
      return
    }
    onChoose(nextFile)
  }, [onChoose])

  const openPicker = () => {
    if (inputRef.current) inputRef.current.value = ""
    inputRef.current?.click()
  }

  const dropFile = (event: React.DragEvent) => {
    event.preventDefault()
    setDragOver(false)
    const nextFile = event.dataTransfer.files[0]
    if (nextFile) chooseFile(nextFile)
  }

  return (
    <MotionStep className="mx-auto max-w-3xl">
      <WizardProgress active={2} />
      <BackButton onClick={onBack} />
      <div className="mb-6">
        <h2 className="text-3xl font-heading tracking-tight">Upload your CV</h2>
        <p className="mt-2 text-muted-foreground">Choose the file first. We only start extracting after you confirm.</p>
      </div>

      <Card>
        <CardContent className="p-6">
          <div
            onDragOver={(event) => { event.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={dropFile}
            className={`rounded-2xl border-2 border-dashed p-8 transition-all ${dragOver ? "border-primary bg-primary/5" : "border-muted-foreground/20 bg-muted/20"}`}
          >
            {!file ? (
              <div className="text-center">
                <div className="mx-auto mb-4 flex size-14 items-center justify-center rounded-full bg-background text-muted-foreground shadow-sm">
                  <Upload className="size-7" />
                </div>
                <p className="font-medium">Drop your CV here</p>
                <p className="mt-1 text-sm text-muted-foreground">or browse for a file on your computer</p>
                <Button type="button" variant="outline" className="mt-5" onClick={openPicker}>
                  Choose file
                </Button>
              </div>
            ) : (
              <div className="flex flex-col gap-5 sm:flex-row sm:items-center">
                <div className="flex size-14 shrink-0 items-center justify-center rounded-2xl bg-primary/10 text-primary">
                  <File className="size-7" />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">{file.name}</p>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {formatSize(file.size)}. {file.type || "File type will be detected"}
                  </p>
                </div>
                <div className="flex gap-2">
                  <Button type="button" variant="outline" onClick={openPicker}>Change file</Button>
                  <Button type="button" variant="ghost" size="icon" onClick={onClear} aria-label="Remove file">
                    <X className="size-4" />
                  </Button>
                </div>
              </div>
            )}
          </div>

          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.md,.docx,.json"
            className="hidden"
            onChange={(event) => {
              const nextFile = event.target.files?.[0]
              if (nextFile) chooseFile(nextFile)
            }}
          />

          <div className="mt-6 flex justify-end">
            <Button type="button" size="lg" disabled={!file || isSubmitting} onClick={onContinue}>
              {isSubmitting ? <Spinner className="mr-2 size-4" /> : null}
              Continue, build profile
            </Button>
          </div>
        </CardContent>
      </Card>
    </MotionStep>
  )
}

function PasteStep({
  text,
  onText,
  onBack,
  onContinue,
  isSubmitting,
}: {
  text: string
  onText: (text: string) => void
  onBack: () => void
  onContinue: () => void
  isSubmitting: boolean
}) {
  const charCount = text.trim().length
  const canContinue = charCount >= MIN_CV_CHARS

  return (
    <MotionStep className="mx-auto max-w-3xl">
      <WizardProgress active={2} />
      <BackButton onClick={onBack} />
      <div className="mb-6">
        <h2 className="text-3xl font-heading tracking-tight">Paste your CV</h2>
        <p className="mt-2 text-muted-foreground">Paste the full CV text. Names, dates, projects, and role details all help.</p>
      </div>
      <Card>
        <CardContent className="p-6">
          <Textarea
            value={text}
            onChange={(event) => onText(event.target.value)}
            placeholder="Paste your CV content here. Include your name, contact details, experience, education, projects, skills, and anything else you want HaxJobs to understand."
            rows={16}
            className="min-h-80 resize-y text-sm leading-6"
            autoFocus
          />
          <div className="mt-3 flex items-center justify-between gap-3">
            <p className={`text-sm ${canContinue ? "text-muted-foreground" : "text-amber-600"}`}>
              {charCount} of {MIN_CV_CHARS} characters minimum
            </p>
            <Button size="lg" disabled={!canContinue || isSubmitting} onClick={onContinue}>
              {isSubmitting ? <Spinner className="mr-2 size-4" /> : null}
              Continue, build profile
            </Button>
          </div>
        </CardContent>
      </Card>
    </MotionStep>
  )
}

function ExtractingStep({ phases, source }: { phases: ExtractionPhase[]; source: Source }) {
  const [active, setActive] = useState(0)
  const labels = phases.length > 0 ? phases.map((phase) => phase.label.replace(/\u2026/g, "")) : DEFAULT_PHASES

  useEffect(() => {
    const timer = window.setInterval(() => {
      setActive((current) => Math.min(current + 1, labels.length - 1))
    }, 900)
    return () => window.clearInterval(timer)
  }, [labels.length])

  return (
    <MotionStep className="mx-auto max-w-3xl">
      <WizardProgress active={2} />
      <Card className="overflow-hidden">
        <CardHeader className="border-b bg-muted/20">
          <CardTitle className="font-heading text-2xl">Building your profile</CardTitle>
          <CardDescription>
            Reading your {source === "upload" ? "file" : "pasted CV"}, extracting what we can, then asking the agent to enrich the useful bits.
          </CardDescription>
        </CardHeader>
        <CardContent className="p-6">
          <div className="space-y-5">
            {labels.map((label, index) => {
              const done = index < active
              const current = index === active
              return (
                <div key={`${label}-${index}`} className="flex items-center gap-4">
                  <div className={`flex size-9 shrink-0 items-center justify-center rounded-full border ${done ? "border-primary bg-primary text-primary-foreground" : current ? "border-primary text-primary" : "border-muted text-muted-foreground"}`}>
                    {done ? <Check className="size-4" /> : current ? <Spinner className="size-4" /> : <Circle className="size-3" />}
                  </div>
                  <div className="flex-1">
                    <p className={done || current ? "font-medium" : "text-muted-foreground"}>{label}</p>
                    {current ? <p className="text-sm text-muted-foreground">Working on this now.</p> : null}
                  </div>
                </div>
              )
            })}
          </div>
        </CardContent>
      </Card>
    </MotionStep>
  )
}

function ReviewStep({
  profile,
  question,
  questionsRemaining,
  isAnswering,
  isCompleting,
  onAnswer,
  onSkipQuestions,
  onComplete,
}: {
  profile: Record<string, unknown>
  question: FieldQuestion | null
  questionsRemaining: number
  isAnswering: boolean
  isCompleting: boolean
  onAnswer: (field: string, answer: string) => void
  onSkipQuestions: () => void
  onComplete: () => void
}) {
  const [answer, setAnswer] = useState("")
  const [showQuestion, setShowQuestion] = useState(Boolean(question))
  const sections = buildSections(profile)
  const completeCount = sections.filter((section) => section.status === "complete").length
  const strength = Math.round((completeCount / sections.length) * 100)

  useEffect(() => {
    setAnswer("")
    setShowQuestion(Boolean(question))
  }, [question?.field])

  return (
    <MotionStep className="mx-auto max-w-4xl">
      <WizardProgress active={3} />
      <div className="mb-6 grid gap-4 lg:grid-cols-[1fr_auto] lg:items-end">
        <div>
          <h2 className="text-3xl font-heading tracking-tight">Review your profile draft</h2>
          <p className="mt-2 text-muted-foreground">
            This is what HaxJobs understood from your CV. Missing does not mean broken. It means we know what to improve next.
          </p>
        </div>
        <Card className="min-w-48 bg-muted/20">
          <CardContent className="p-4">
            <p className="text-sm text-muted-foreground">Profile strength</p>
            <p className="text-3xl font-semibold">{strength}%</p>
          </CardContent>
        </Card>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {sections.map((section) => (
          <Card key={section.key} className="shadow-sm">
            <CardHeader className="pb-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <CardTitle className="text-base">{section.title}</CardTitle>
                  <CardDescription className="mt-1 line-clamp-2">{section.summary}</CardDescription>
                </div>
                {statusBadge(section.status)}
              </div>
            </CardHeader>
            {section.details.length > 0 ? (
              <CardContent className="pt-0">
                <div className="flex flex-wrap gap-2">
                  {section.details.slice(0, 8).map((detail) => (
                    <Badge key={detail} variant="outline" className="max-w-full truncate font-normal">
                      {detail}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            ) : null}
          </Card>
        ))}
      </div>

      {question && showQuestion ? (
        <Card className="mt-6 border-primary/30 bg-primary/5">
          <CardHeader>
            <CardTitle className="font-heading text-xl">Improve your profile</CardTitle>
            <CardDescription>{questionsRemaining} useful follow up{questionsRemaining === 1 ? "" : "s"} left. Answer what you can, skip what you want.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <p className="font-medium">{question.question}</p>
              <p className="mt-1 text-sm text-muted-foreground">{question.description}</p>
            </div>
            {question.type === "list" ? (
              <Textarea value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Add a few items, separated with commas." rows={3} autoFocus />
            ) : (
              <Input value={answer} onChange={(event) => setAnswer(event.target.value)} placeholder="Type your answer." autoFocus />
            )}
            <div className="flex flex-wrap gap-2">
              <Button disabled={!answer.trim() || isAnswering} onClick={() => onAnswer(question.field, answer.trim())}>
                {isAnswering ? <Spinner className="mr-2 size-4" /> : null}
                Save answer
              </Button>
              <Button variant="ghost" onClick={onSkipQuestions}>Skip questions for now</Button>
            </div>
          </CardContent>
        </Card>
      ) : null}

      <div className="mt-6 flex justify-end">
        <Button size="lg" onClick={onComplete} disabled={isCompleting}>
          {isCompleting ? <Spinner className="mr-2 size-4" /> : null}
          Save profile and finish
        </Button>
      </div>
    </MotionStep>
  )
}

function CompleteStep() {
  const navigate = useNavigate()

  useEffect(() => {
    const timer = window.setTimeout(() => navigate("/", { replace: true }), 2500)
    return () => window.clearTimeout(timer)
  }, [navigate])

  return (
    <MotionStep className="mx-auto max-w-xl text-center">
      <div className="py-12">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="mx-auto mb-5 flex size-20 items-center justify-center rounded-full bg-primary/10 text-5xl"
        >
          ✅
        </motion.div>
        <h2 className="text-3xl font-heading tracking-tight">Profile saved</h2>
        <p className="mt-2 text-muted-foreground">Nice. HaxJobs has something real to work with now. Opening the dashboard...</p>
      </div>
    </MotionStep>
  )
}

function asRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === "object" && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function asArray(value: unknown): unknown[] {
  return Array.isArray(value) ? value : []
}

function text(value: unknown): string {
  return typeof value === "string" ? value.trim() : ""
}

function itemName(item: unknown): string {
  if (typeof item === "string") return item.trim()
  const record = asRecord(item)
  return text(record.name) || text(record.title) || text(record.company) || text(record.institution) || text(record.degree)
}

function collectNames(value: unknown, limit = 6): string[] {
  return asArray(value).map(itemName).filter(Boolean).slice(0, limit)
}

function joinOrMissing(values: string[], missing = "Nothing clear yet") {
  return values.length ? values.join(", ") : missing
}

function profileValue(profile: Record<string, unknown>, path: string): unknown {
  return path.split(".").reduce<unknown>((current, part) => asRecord(current)[part], profile)
}

function sectionStatus(hasCore: boolean, hasSomething: boolean): SectionStatus {
  if (hasCore) return "complete"
  if (hasSomething) return "review"
  return "missing"
}

function buildSections(profile: Record<string, unknown>): ReviewSection[] {
  const personal = asRecord(profile.personal)
  const preferences = asRecord(profile.preferences)
  const authorization = asRecord(profile.work_authorization)
  const skills = asRecord(profile.skills)
  const health = asRecord(profile.profile_health)

  const name = text(personal.name)
  const email = text(personal.email)
  const location = text(personal.location)
  const headline = text(personal.preferred_headline) || text(personal.summary)
  const roles = collectNames(preferences.preferred_roles)
  const preferredLocations = collectNames(preferences.preferred_locations)
  const workModes = collectNames(preferences.preferred_work_modes)
  const authStatus = text(authorization.status) || text(profileValue(profile, "work_authorization.summary"))
  const education = collectNames(profile.education, 4)
  const projects = collectNames(profile.projects, 5)
  const experience = asArray(profile.work_experience)
  const experienceNames = experience.map((item) => {
    const role = asRecord(item)
    return [text(role.title), text(role.company)].filter(Boolean).join(" at ")
  }).filter(Boolean).slice(0, 5)

  const skillNames = ["languages", "frameworks", "databases", "devops", "ai_ml", "tools", "soft_skills"]
    .flatMap((category) => collectNames(skills[category], 4))
    .filter(Boolean)

  const missingCount = Number(asRecord(health.required_fields).missing_count ?? 0)
  const completion = Number(health.completion_pct ?? 0)

  return [
    {
      key: "personal",
      title: "Personal details",
      status: sectionStatus(Boolean(name && email && location), Boolean(name || email || location || headline)),
      summary: [name, location].filter(Boolean).join(". ") || "Name, email, and location still need checking.",
      details: [email, headline].filter(Boolean),
    },
    {
      key: "target",
      title: "Target roles",
      status: sectionStatus(roles.length > 0, roles.length > 0 || preferredLocations.length > 0 || workModes.length > 0),
      summary: joinOrMissing(roles, "Target roles are still missing."),
      details: [...preferredLocations.map((item) => `Location: ${item}`), ...workModes.map((item) => `Mode: ${item}`)],
    },
    {
      key: "authorization",
      title: "Work authorization",
      status: sectionStatus(Boolean(authStatus), Boolean(authStatus)),
      summary: authStatus || "Visa or work authorization status is missing.",
      details: [],
    },
    {
      key: "skills",
      title: "Skills",
      status: sectionStatus(skillNames.length > 0, skillNames.length > 0),
      summary: skillNames.length ? `${skillNames.length} skills found` : "No clear skills extracted yet.",
      details: skillNames.slice(0, 10),
    },
    {
      key: "experience",
      title: "Experience",
      status: sectionStatus(experience.length > 0, experience.length > 0),
      summary: experience.length ? `${experience.length} role${experience.length === 1 ? "" : "s"} found` : "No work history found yet.",
      details: experienceNames,
    },
    {
      key: "education",
      title: "Education",
      status: sectionStatus(education.length > 0, education.length > 0),
      summary: joinOrMissing(education, "No education section found yet."),
      details: education,
    },
    {
      key: "projects",
      title: "Projects",
      status: sectionStatus(projects.length > 0, projects.length > 0),
      summary: joinOrMissing(projects, "No projects found yet."),
      details: projects,
    },
    {
      key: "health",
      title: "Profile health",
      status: sectionStatus(missingCount === 0 && completion > 0, completion > 0),
      summary: completion ? `${completion}% complete. ${missingCount} required field${missingCount === 1 ? "" : "s"} missing.` : "Health score will improve as the profile fills out.",
      details: [],
    },
  ]
}

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>("welcome")
  const [source, setSource] = useState<Source>("upload")
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [pastedText, setPastedText] = useState("")
  const [response, setResponse] = useState<ExtractResponse | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    fetch("/api/onboarding/status")
      .then((result) => result.json())
      .then((data) => {
        if (data.stage === "complete") navigate("/", { replace: true })
      })
      .catch(() => undefined)
  }, [navigate])

  const showReview = (data: ExtractResponse) => {
    setResponse(data)
    window.setTimeout(() => setStep("review"), 900)
  }

  const uploadMutation = useMutation({
    mutationFn: uploadCV,
    onSuccess: showReview,
    onError: (error: Error) => {
      toast.error(error.message)
      setStep("upload")
    },
  })

  const pasteMutation = useMutation({
    mutationFn: extractText,
    onSuccess: showReview,
    onError: (error: Error) => {
      toast.error(error.message)
      setStep("paste")
    },
  })

  const answerMutation = useMutation({
    mutationFn: ({ field, answer }: { field: string; answer: string }) => submitAnswer(field, answer),
    onSuccess: (data) => setResponse((previous) => previous ? { ...previous, ...data } : previous),
    onError: (error: Error) => toast.error(error.message),
  })

  const completeMutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: () => setStep("complete"),
    onError: (error: Error) => toast.error(error.message),
  })

  const beginUpload = () => {
    if (!selectedFile) return
    setSource("upload")
    setStep("extracting")
    uploadMutation.mutate(selectedFile)
  }

  const beginPaste = () => {
    const text = pastedText.trim()
    if (text.length < MIN_CV_CHARS) return
    setSource("paste")
    setStep("extracting")
    pasteMutation.mutate(text)
  }

  const chooseSource = (nextSource: Source) => {
    setSource(nextSource)
    setStep(nextSource)
  }

  const skipQuestions = () => {
    setResponse((previous) => previous ? { ...previous, next_question: null, questions_remaining: 0 } : previous)
    toast.message("Questions skipped. You can enrich the profile later.")
  }

  return (
    <div className="min-h-[calc(100vh-4rem)] px-4 py-8 sm:px-6 lg:px-8">
      <AnimatePresence mode="wait">
        {step === "welcome" ? <WelcomeStep key="welcome" onNext={() => setStep("source")} /> : null}
        {step === "source" ? <SourceStep key="source" onSelect={chooseSource} /> : null}
        {step === "upload" ? (
          <UploadStep
            key="upload"
            file={selectedFile}
            onChoose={setSelectedFile}
            onClear={() => setSelectedFile(null)}
            onBack={() => setStep("source")}
            onContinue={beginUpload}
            isSubmitting={uploadMutation.isPending}
          />
        ) : null}
        {step === "paste" ? (
          <PasteStep
            key="paste"
            text={pastedText}
            onText={setPastedText}
            onBack={() => setStep("source")}
            onContinue={beginPaste}
            isSubmitting={pasteMutation.isPending}
          />
        ) : null}
        {step === "extracting" ? (
          <ExtractingStep key="extracting" source={source} phases={response?.extraction_phases || []} />
        ) : null}
        {step === "review" && response ? (
          <ReviewStep
            key="review"
            profile={response.profile}
            question={response.next_question}
            questionsRemaining={response.questions_remaining}
            isAnswering={answerMutation.isPending}
            isCompleting={completeMutation.isPending}
            onAnswer={(field, answer) => answerMutation.mutate({ field, answer })}
            onSkipQuestions={skipQuestions}
            onComplete={() => completeMutation.mutate()}
          />
        ) : null}
        {step === "complete" ? <CompleteStep key="complete" /> : null}
      </AnimatePresence>
    </div>
  )
}
