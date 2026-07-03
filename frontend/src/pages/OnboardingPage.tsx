import { useState, useCallback, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQuery } from "@tanstack/react-query"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"

// ── types ──

type Step = "welcome" | "source" | "extracting" | "review" | "complete"

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

// ── API helpers ──

const API = "/api"

async function uploadCV(file: File): Promise<ExtractResponse> {
  const form = new FormData()
  form.append("file", file)
  const r = await fetch(`${API}/onboarding/upload`, { method: "POST", body: form })
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Upload failed" }))
    throw new Error(e.detail || "Upload failed")
  }
  return r.json()
}

async function extractText(text: string): Promise<ExtractResponse> {
  const r = await fetch(`${API}/onboarding/extract-text`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text }),
  })
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Extraction failed" }))
    throw new Error(e.detail || "Extraction failed")
  }
  return r.json()
}

async function submitAnswer(questionId: string, answer: string): Promise<{
  profile: Record<string, unknown>
  next_question: FieldQuestion | null
  questions_remaining: number
  phase: string
}> {
  const r = await fetch(`${API}/onboarding/wizard`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question_id: questionId, answer }),
  })
  if (!r.ok) throw new Error("Failed to submit answer")
  return r.json()
}

async function completeOnboarding() {
  const r = await fetch(`${API}/onboarding/complete`, { method: "POST" })
  if (!r.ok) throw new Error("Failed to complete")
  return r.json()
}

async function getStatus() {
  const r = await fetch(`${API}/onboarding/status`)
  return r.json()
}

// ── animations ──

const stepVariants = {
  enter: { opacity: 0, x: 24, scale: 0.98 },
  center: { opacity: 1, x: 0, scale: 1 },
  exit: { opacity: 0, x: -24, scale: 0.98 },
}

const fadeIn = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: i * 0.1, duration: 0.3 },
  }),
}

// ── STEP 1: Welcome ──

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <Card className="border-border/60">
        <CardHeader className="text-center pb-4">
          <CardTitle className="text-2xl font-heading">Welcome to HaxJobs</CardTitle>
          <CardDescription className="text-base max-w-sm mx-auto">
            Your profile drives everything. We&apos;ll extract it from your CV, enrich it
            with AI, and show you the draft before using it.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-3">
          <ul className="text-sm text-muted-foreground space-y-1.5 list-disc list-inside">
            <li>Watches company boards every day</li>
            <li>Scores every role 0–100 against your profile</li>
            <li>Never auto-applies — you&apos;re always in control</li>
          </ul>
          <Button onClick={onNext} size="lg" className="w-full mt-2">
            Build my profile
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ── STEP 2: Choose source ──

function SourceStep({
  onFile,
  onPaste,
}: {
  onFile: (f: File) => void
  onPaste: () => void
}) {
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const file = e.dataTransfer.files[0]
      if (file) onFile(file)
    },
    [onFile],
  )

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <StepIndicator step={2} total={5} />
      <h2 className="text-xl font-heading text-center mb-2">
        How should HaxJobs learn about your background?
      </h2>
      <p className="text-sm text-muted-foreground text-center mb-6 max-w-sm mx-auto">
        Choose the easiest starting point. We&apos;ll show you what we extract before using it, and your edits always win.
      </p>

      {/* 2x2 grid */}
      <div className="grid grid-cols-2 gap-3">
        {/* Upload CV */}
        <button
          onClick={() => inputRef.current?.click()}
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`flex flex-col items-start gap-2 p-4 rounded-xl border-2 text-left transition-all duration-200 cursor-pointer
            ${dragOver
              ? "border-primary bg-primary/5 scale-[1.02]"
              : "border-border hover:border-primary/30 hover:bg-muted/20"
            }`}
        >
          <span className="text-2xl">📄</span>
          <span className="font-medium text-sm">Upload CV</span>
          <span className="text-xs text-muted-foreground">PDF, DOCX, or text</span>
          <Badge variant="secondary" className="text-[10px] mt-1">FASTEST</Badge>
        </button>

        {/* Paste text */}
        <button
          onClick={onPaste}
          className="flex flex-col items-start gap-2 p-4 rounded-xl border border-border hover:border-primary/30 hover:bg-muted/20 text-left transition-all duration-200 cursor-pointer"
        >
          <span className="text-2xl">📝</span>
          <span className="font-medium text-sm">Paste CV text</span>
          <span className="text-xs text-muted-foreground">Best if your file isn&apos;t readable</span>
          <Badge variant="secondary" className="text-[10px] mt-1">EASY</Badge>
        </button>

        {/* LinkedIn */}
        <button
          disabled
          className="flex flex-col items-start gap-2 p-4 rounded-xl border border-border bg-muted/30 text-left cursor-not-allowed opacity-50"
        >
          <span className="text-2xl">🔗</span>
          <span className="font-medium text-sm">Use LinkedIn</span>
          <span className="text-xs text-muted-foreground">Paste public profile URL</span>
          <Badge variant="outline" className="text-[10px] mt-1">SOON</Badge>
        </button>

        {/* Manual */}
        <button
          disabled
          className="flex flex-col items-start gap-2 p-4 rounded-xl border border-border bg-muted/30 text-left cursor-not-allowed opacity-50"
        >
          <span className="text-2xl">✍️</span>
          <span className="font-medium text-sm">Enter manually</span>
          <span className="text-xs text-muted-foreground">Skip CV entirely</span>
          <Badge variant="outline" className="text-[10px] mt-1">SOON</Badge>
        </button>
      </div>

      <p className="text-xs text-center text-muted-foreground mt-6">
        Your profile stays on your machine. HaxJobs never applies or sends outreach without your approval.
      </p>

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md,.docx,.json"
        className="hidden"
        onChange={(e) => {
          const file = e.target.files?.[0]
          if (file) onFile(file)
        }}
      />
    </motion.div>
  )
}

// ── STEP 2b: Paste text sub-step ──

function PasteStep({
  onSubmit,
  isSubmitting,
}: {
  onSubmit: (text: string) => void
  isSubmitting: boolean
}) {
  const [text, setText] = useState("")

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <StepIndicator step={2} total={5} />
      <Card className="border-border/60">
        <CardHeader className="pb-2">
          <CardTitle className="text-lg font-heading">Paste your CV text</CardTitle>
          <CardDescription>
            Copy the full text from your CV/PDF and paste it here.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            placeholder="Paste your CV content here…"
            rows={12}
            className="resize-none"
            autoFocus
          />
          <Button
            onClick={() => text.trim().length >= 100 && onSubmit(text.trim())}
            disabled={text.trim().length < 100 || isSubmitting}
            className="w-full"
          >
            {isSubmitting ? <Spinner className="size-4 mr-2" /> : null}
            Extract my profile
          </Button>
          {text.trim().length > 0 && text.trim().length < 100 && (
            <p className="text-xs text-muted-foreground text-center">
              CV text too short — need at least 100 characters for meaningful extraction
            </p>
          )}
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ── STEP 3: Extracting ──

function ExtractingStep({ phases }: { phases: ExtractionPhase[] }) {
  const [visible, setVisible] = useState(0)

  useEffect(() => {
    if (visible >= phases.length) return
    const t = setTimeout(() => setVisible((v) => v + 1), 500)
    return () => clearTimeout(t)
  }, [visible, phases.length])

  const displayPhases = phases.length > 0 ? phases : [
    { phase: "reading", label: "Reading your CV…", done: false },
    { phase: "extracting", label: "Extracting details…", done: false },
    { phase: "agent_enriching", label: "Enriching with AI…", done: false },
    { phase: "generating_questions", label: "Profile draft ready", done: false },
  ]

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <Card className="border-border/60">
        <CardContent className="flex flex-col py-12 gap-3">
          <h2 className="text-lg font-heading text-center mb-4">
            Building your profile…
          </h2>
          {displayPhases.map((p, i) => (
            <motion.div
              key={p.phase}
              custom={i}
              variants={fadeIn}
              initial="hidden"
              animate={i < visible ? "visible" : "hidden"}
              className="flex items-center gap-3"
            >
              <span className={`text-sm min-w-[220px] ${i < visible ? "text-foreground" : "text-muted-foreground/40"}`}>
                {p.label}
              </span>
              <div className="flex-1 h-1.5 rounded-full bg-muted overflow-hidden">
                <motion.div
                  className="h-full rounded-full bg-primary"
                  initial={{ width: "0%" }}
                  animate={{ width: i < visible ? "100%" : "0%" }}
                  transition={{ duration: 0.4 }}
                />
              </div>
              {i < visible && <span className="text-xs text-primary font-medium">Done</span>}
            </motion.div>
          ))}
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ── STEP 4: Review ──

function ReviewStep({
  profile,
  questions,
  questionsRemaining,
  onSubmitAnswer,
  onSkipQuestions,
  onComplete,
  isCompleting,
}: {
  profile: Record<string, unknown>
  questions: FieldQuestion | null
  questionsRemaining: number
  onSubmitAnswer: (questionId: string, answer: string) => void
  onSkipQuestions: () => void
  onComplete: () => void
  isCompleting: boolean
}) {
  const [showQuestions, setShowQuestions] = useState(false)
  const [answerValue, setAnswerValue] = useState("")

  const sections = buildSections(profile as Record<string, unknown>)

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <StepIndicator step={4} total={5} />
      <h2 className="text-xl font-heading text-center mb-2">
        Here&apos;s what we built from your CV
      </h2>
      <p className="text-sm text-muted-foreground text-center mb-6 max-w-sm mx-auto">
        Edit anything, or skip — you can always refine it later from the dashboard.
      </p>

      {/* Profile sections */}
      <div className="space-y-3 mb-6">
        {sections.map((s) => (
          <div key={s.key} className="border border-border rounded-lg p-3">
            <div className="flex items-center justify-between mb-1">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{s.label}</span>
                {s.status === "complete" && (
                  <Badge variant="outline" className="text-[10px] border-green-500/30 text-green-600">
                    ✓
                  </Badge>
                )}
                {s.status === "gap" && (
                  <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-600">
                    ⚠ gap
                  </Badge>
                )}
              </div>
              {s.status !== "empty" && (
                <span className="text-[10px] text-muted-foreground">{s.meta}</span>
              )}
            </div>
            {s.status === "empty" ? (
              <p className="text-xs text-muted-foreground italic">Not provided</p>
            ) : typeof s.value === "string" ? (
              <p className="text-xs text-muted-foreground line-clamp-2">{s.value}</p>
            ) : Array.isArray(s.value) ? (
              <div className="flex flex-wrap gap-1 mt-1">
                {s.value.slice(0, 8).map((item, i) => (
                  <Badge key={i} variant="secondary" className="text-[10px]">
                    {typeof item === "string" ? item : (item as Record<string, unknown>).name as string || String(item)}
                  </Badge>
                ))}
                {s.value.length > 8 && (
                  <Badge variant="outline" className="text-[10px]">+{s.value.length - 8}</Badge>
                )}
              </div>
            ) : null}
          </div>
        ))}
      </div>

      {/* Deep questions (optional) */}
      {showQuestions && questions && (
        <Card className="border-primary/20 bg-primary/5 mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-heading">{questions.question}</CardTitle>
            <CardDescription className="text-xs">{questions.description}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {questions.type === "list" ? (
              <Textarea
                value={answerValue}
                onChange={(e) => setAnswerValue(e.target.value)}
                placeholder="Comma-separated values…"
                rows={2}
                autoFocus
              />
            ) : (
              <Input
                value={answerValue}
                onChange={(e) => setAnswerValue(e.target.value)}
                placeholder="Your answer…"
                autoFocus
              />
            )}
            <div className="flex gap-2">
              <Button
                size="sm"
                variant="default"
                disabled={!answerValue.trim()}
                onClick={() => {
                  onSubmitAnswer(questions.field, answerValue.trim())
                  setAnswerValue("")
                }}
              >
                Save & Continue
              </Button>
              <Button size="sm" variant="ghost" onClick={onSkipQuestions}>
                Skip questions
              </Button>
            </div>
            {questionsRemaining > 0 && (
              <p className="text-[10px] text-muted-foreground">
                {questionsRemaining} more question{questionsRemaining !== 1 ? "s" : ""} after this
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {!showQuestions && questions && questionsRemaining > 0 && (
        <Button
          variant="outline"
          className="w-full mb-4"
          onClick={() => setShowQuestions(true)}
        >
          Answer {questionsRemaining} deep question{questionsRemaining !== 1 ? "s" : ""} to improve your profile
        </Button>
      )}

      <Button onClick={onComplete} className="w-full" size="lg" disabled={isCompleting}>
        {isCompleting ? <Spinner className="size-4 mr-2" /> : null}
        Looks good — finish
      </Button>
    </motion.div>
  )
}

// ── STEP 5: Complete ──

function CompleteStep() {
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => navigate("/"), 2500)
    return () => clearTimeout(t)
  }, [navigate])

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <Card className="border-primary/20 bg-primary/5">
        <CardContent className="flex flex-col items-center py-16 gap-4 text-center">
          <motion.div
            initial={{ scale: 0 }}
            animate={{ scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 15 }}
            className="text-6xl"
          >
            ✅
          </motion.div>
          <h2 className="text-2xl font-heading">You&apos;re all set!</h2>
          <p className="text-muted-foreground max-w-xs">
            Your profile is ready. Redirecting you to the dashboard…
          </p>
        </CardContent>
      </Card>
    </motion.div>
  )
}

// ── helpers ──

function StepIndicator({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center justify-center gap-1 mb-4">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full transition-all duration-300 ${
            i < step
              ? "w-6 bg-primary"
              : i === step - 1
                ? "w-8 bg-primary"
                : "w-4 bg-muted"
          }`}
        />
      ))}
    </div>
  )
}

interface ProfileSection {
  key: string
  label: string
  status: "complete" | "gap" | "partial" | "empty"
  value: string | unknown[] | null
  meta: string
}

function buildSections(profile: Record<string, unknown>): ProfileSection[] {
  // Required fields to check
  const requiredFields: [string, string][] = [
    ["personal.name", "Name"],
    ["personal.email", "Email"],
    ["personal.location", "Location"],
    ["preferences.preferred_roles", "Target Roles"],
    ["preferences.preferred_locations", "Preferred Locations"],
    ["preferences.preferred_work_modes", "Work Mode"],
    ["work_authorization.summary", "Work Authorization"],
  ]

  const sections: ProfileSection[] = []

  for (const [path, label] of requiredFields) {
    const val = getNested(profile, path)
    const isEmpty = val === null || val === undefined || val === "" || (Array.isArray(val) && val.length === 0)
    sections.push({
      key: path,
      label,
      status: isEmpty ? "gap" : "complete",
      value: val as string | unknown[] | null,
      meta: "",
    })
  }

  // Skills summary
  const skills = (profile as Record<string, unknown>).skills as Record<string, unknown> | undefined
  if (skills) {
    const total = countSkills(skills)
    sections.push({ key: "skills", label: "Skills", status: total > 0 ? "complete" : "gap", value: null, meta: `${total} found` })
  }

  // Work experience summary
  const work = (profile as Record<string, unknown>).work_experience as Record<string, unknown>[] | undefined
  if (work && work.length > 0) {
    const titles = work.map((w) => `${String(w.title || "Role")} @ ${String(w.company || "Company")}`).join(", ")
    sections.push({ key: "work", label: "Experience", status: "complete", value: titles, meta: `${work.length} role${work.length > 1 ? "s" : ""}` })
  } else {
    sections.push({ key: "work", label: "Experience", status: "empty", value: null, meta: "" })
  }

  // Education
  const edu = (profile as Record<string, unknown>).education as Record<string, unknown>[] | undefined
  if (edu && edu.length > 0) {
    sections.push({ key: "education", label: "Education", status: "complete", value: null, meta: `${edu.length} entr${edu.length > 1 ? "ies" : "y"}` })
  }

  return sections
}

function getNested(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split(".")
  let current: unknown = obj
  for (const p of parts) {
    if (current && typeof current === "object") {
      current = (current as Record<string, unknown>)[p]
    } else {
      return null
    }
  }
  return current
}

function countSkills(skills: Record<string, unknown>): number {
  let count = 0
  for (const cat of ["languages", "frameworks", "databases", "devops", "ai_ml", "tools"]) {
    const arr = skills[cat] as unknown[] | undefined
    if (arr) count += arr.length
  }
  return count
}

// ── main page ──

// ponytail: local state machine is simpler than react-router sub-routes for a linear flow
type Source = "file" | "paste" | undefined

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>("welcome")
  const [source, setSource] = useState<Source>()
  const [response, setResponse] = useState<ExtractResponse | null>(null)
  const navigate = useNavigate()

  // Check if already onboarded
  const { data: status } = useQuery({
    queryKey: ["onboarding-status"],
    queryFn: getStatus,
    staleTime: 10_000,
  })

  const uploadMutation = useMutation({
    mutationFn: uploadCV,
    onSuccess: (data) => {
      setResponse(data)
      setStep("extracting")
      // Simulate progress then move to review
      setTimeout(() => setStep("review"), 2500)
    },
    onError: (e: Error) => {
      toast.error(e.message)
      setStep("source")
    },
  })

  const pasteMutation = useMutation({
    mutationFn: extractText,
    onSuccess: (data) => {
      setResponse(data)
      setStep("extracting")
      setTimeout(() => setStep("review"), 2500)
    },
    onError: (e: Error) => {
      toast.error(e.message)
      setStep("source")
    },
  })

  const answerMutation = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) => submitAnswer(id, answer),
    onSuccess: (data) => {
      setResponse((prev) => prev ? { ...prev, ...data } : prev)
      if (!data.next_question) {
        // Press "Looks good" equivalent — show complete step after answering
      }
    },
    onError: () => toast.error("Failed to save answer"),
  })

  const completeMutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: () => setStep("complete"),
    onError: () => toast.error("Failed to save profile"),
  })

  const handleFile = (file: File) => {
    if (file.size > 5 * 1024 * 1024) {
      toast.error("File too large — max 5 MB")
      return
    }
    setSource("file")
    uploadMutation.mutate(file)
  }

  // Redirect if already complete
  if (status?.stage === "complete") {
    navigate("/", { replace: true })
    return null
  }

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] p-4">
      <div className="w-full max-w-lg">
        <AnimatePresence mode="wait">
          {step === "welcome" && <WelcomeStep onNext={() => setStep("source")} />}

          {step === "source" && (
            source === "paste" ? (
              <PasteStep
                key="paste"
                onSubmit={(text) => pasteMutation.mutate(text)}
                isSubmitting={pasteMutation.isPending}
              />
            ) : (
              <SourceStep
                key="source"
                onFile={handleFile}
                onPaste={() => setSource("paste")}
              />
            )
          )}

          {step === "extracting" && (
            <ExtractingStep phases={response?.extraction_phases || []} />
          )}

          {step === "review" && response && (
            <ReviewStep
              profile={response.profile}
              questions={response.next_question}
              questionsRemaining={response.questions_remaining}
              onSubmitAnswer={(id, answer) => answerMutation.mutate({ id, answer })}
              onSkipQuestions={() => {}}
              onComplete={() => completeMutation.mutate()}
              isCompleting={completeMutation.isPending}
            />
          )}

          {step === "complete" && <CompleteStep />}
        </AnimatePresence>
      </div>
    </div>
  )
}
