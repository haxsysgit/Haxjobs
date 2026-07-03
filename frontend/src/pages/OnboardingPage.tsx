import { useState, useCallback, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation } from "@tanstack/react-query"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Badge } from "@/components/ui/badge"
import { Spinner } from "@/components/ui/spinner"
import { ArrowLeft, Upload, FileText, File, X, Check } from "lucide-react"

// ── types ──

type Step = "welcome" | "source" | "upload" | "paste" | "extracting" | "review" | "complete"

type Source = "upload" | "paste"

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

// ── animations ──

const stepVariants = {
  enter: { opacity: 0, x: 24 },
  center: { opacity: 1, x: 0 },
  exit: { opacity: 0, x: -24 },
}

// ── shared components ──

function StepProgress({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center gap-1 mb-8">
      {Array.from({ length: total }, (_, i) => (
        <div
          key={i}
          className={`h-1 rounded-full transition-all duration-300 ${
            i < step ? "w-8 bg-primary" : i === step - 1 ? "w-10 bg-primary" : "w-4 bg-muted-foreground/20"
          }`}
        />
      ))}
    </div>
  )
}

function BackButton({ onClick, label = "Back" }: { onClick: () => void; label?: string }) {
  return (
    <Button variant="ghost" size="sm" onClick={onClick} className="mb-4 -ml-2 text-muted-foreground">
      <ArrowLeft className="size-4 mr-1" />
      {label}
    </Button>
  )
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

// ── STEP 1: Welcome ──

function WelcomeStep({ onNext }: { onNext: () => void }) {
  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-xl mx-auto">
      <div className="text-center space-y-4">
        <div className="text-5xl mb-2">👋</div>
        <h1 className="text-3xl font-heading tracking-tight">Let&apos;s build your profile</h1>
        <p className="text-muted-foreground max-w-md mx-auto leading-relaxed">
          HaxJobs needs to understand your skills, experience, and what you&apos;re
          looking for. So it can find the right jobs and tailor applications to you.
        </p>
        <div className="bg-muted/40 rounded-xl p-5 text-left max-w-sm mx-auto space-y-3 text-sm mt-6">
          <p className="font-medium text-foreground">This takes about 2 minutes:</p>
          <ol className="space-y-2 list-decimal list-inside text-muted-foreground">
            <li>Upload or paste your CV. We extract everything we can</li>
            <li>We enrich it with AI to fill in gaps</li>
            <li>You review, edit, and confirm. Your edits always win</li>
          </ol>
        </div>
        <Button onClick={onNext} size="lg" className="mt-4 min-w-[200px]">
          Get started
        </Button>
      </div>
    </motion.div>
  )
}

// ── STEP 2: Choose source ──

function SourceStep({ onSelect }: { onSelect: (source: Source) => void }) {
  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-xl mx-auto">
      <StepProgress step={1} total={4} />
      <h2 className="text-xl font-heading text-center mb-2">Where&apos;s your CV?</h2>
      <p className="text-sm text-muted-foreground text-center mb-8">
        We&apos;ll extract your profile automatically. You review and edit before saving.
      </p>

      <div className="grid grid-cols-2 gap-4">
        <button
          onClick={() => onSelect("upload")}
          className="flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-border hover:border-primary/40 hover:bg-muted/20 text-center transition-all duration-200 cursor-pointer group"
        >
          <div className="p-3 rounded-full bg-primary/10 group-hover:bg-primary/15 transition-colors">
            <Upload className="size-6 text-primary" />
          </div>
          <div>
            <p className="font-medium">Upload a file</p>
            <p className="text-xs text-muted-foreground mt-1">PDF, DOCX, or text</p>
          </div>
          <Badge variant="secondary" className="text-[10px]">Recommended</Badge>
        </button>

        <button
          onClick={() => onSelect("paste")}
          className="flex flex-col items-center gap-3 p-6 rounded-xl border-2 border-border hover:border-primary/40 hover:bg-muted/20 text-center transition-all duration-200 cursor-pointer group"
        >
          <div className="p-3 rounded-full bg-primary/10 group-hover:bg-primary/15 transition-colors">
            <FileText className="size-6 text-primary" />
          </div>
          <div>
            <p className="font-medium">Paste as text</p>
            <p className="text-xs text-muted-foreground mt-1">Copy and paste CV content</p>
          </div>
        </button>
      </div>
    </motion.div>
  )
}

// ── STEP 3a: Upload file ──

function UploadStep({
  onBack,
  onSubmit,
  isSubmitting,
}: {
  onBack: () => void
  onSubmit: (file: File) => void
  isSubmitting: boolean
}) {
  const [file, setFile] = useState<File | null>(null)
  const [dragOver, setDragOver] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleFile = useCallback((f: File) => {
    if (f.size > 5 * 1024 * 1024) {
      toast.error("File too large. Max 5 MB")
      return
    }
    setFile(f)
  }, [])

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault()
      setDragOver(false)
      const f = e.dataTransfer.files[0]
      if (f) handleFile(f)
    },
    [handleFile],
  )

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-xl mx-auto">
      <StepProgress step={2} total={4} />
      <BackButton onClick={onBack} />

      <h2 className="text-xl font-heading mb-1">Upload your CV</h2>
      <p className="text-sm text-muted-foreground mb-6">
        PDF, DOCX, or plain text. We handle all common formats.
      </p>

      {!file ? (
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
            ${dragOver
              ? "border-primary bg-primary/5 scale-[1.01]"
              : "border-muted-foreground/20 hover:border-primary/30 hover:bg-muted/20"
            }`}
        >
          <Upload className="size-8 mx-auto mb-3 text-muted-foreground" />
          <p className="font-medium mb-1">Drag & drop your CV here</p>
          <p className="text-sm text-muted-foreground">or click to browse files</p>
        </div>
      ) : (
        <div className="border rounded-xl p-4 space-y-3">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <File className="size-5 text-primary" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium text-sm truncate">{file.name}</p>
              <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="size-8"
              onClick={(e) => { e.stopPropagation(); setFile(null) }}
            >
              <X className="size-4" />
            </Button>
          </div>
        </div>
      )}

      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,.md,.docx,.json"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0]
          if (f) handleFile(f)
        }}
      />

      <div className="mt-6 flex gap-3 justify-end">
        {file && (
          <Button onClick={() => onSubmit(file)} disabled={isSubmitting} className="min-w-[140px]">
            {isSubmitting ? <Spinner className="size-4 mr-2" /> : null}
            {isSubmitting ? "Extracting…" : "Extract my profile"}
          </Button>
        )}
        {!file && (
          <Button disabled className="min-w-[140px]">
            Select a file to continue
          </Button>
        )}
      </div>
    </motion.div>
  )
}

// ── STEP 3b: Paste text ──

function PasteStep({
  onBack,
  onSubmit,
  isSubmitting,
}: {
  onBack: () => void
  onSubmit: (text: string) => void
  isSubmitting: boolean
}) {
  const [text, setText] = useState("")

  const charCount = text.trim().length
  const canSubmit = charCount >= 100

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-xl mx-auto">
      <StepProgress step={2} total={4} />
      <BackButton onClick={onBack} />

      <h2 className="text-xl font-heading mb-1">Paste your CV</h2>
      <p className="text-sm text-muted-foreground mb-6">
        Copy the full content of your CV and paste it below.
      </p>

      <Textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        placeholder="Paste your CV content here…&#10;&#10;Example:&#10;John Doe&#10;Email: john@example.com&#10;Location: London, UK&#10;&#10;Software Engineer with 5 years of experience…"
        rows={14}
        className="resize-none font-mono text-sm"
        autoFocus
      />

      <div className="flex items-center justify-between mt-3 mb-6">
        <p className={`text-xs ${canSubmit ? "text-muted-foreground" : "text-amber-600"}`}>
          {charCount} / 100 characters minimum
          {canSubmit ? <Check className="size-3 inline ml-1 text-green-500" /> : null}
        </p>
      </div>

      <div className="flex gap-3 justify-end">
        <Button
          onClick={() => onSubmit(text.trim())}
          disabled={!canSubmit || isSubmitting}
          className="min-w-[140px]"
        >
          {isSubmitting ? <Spinner className="size-4 mr-2" /> : null}
          {isSubmitting ? "Extracting…" : "Extract my profile"}
        </Button>
      </div>
    </motion.div>
  )
}

// ── STEP 4: Extracting ──

const EXTRACT_PHASES = [
  { phase: "reading", label: "Reading your CV" },
  { phase: "extracting", label: "Extracting skills & experience" },
  { phase: "agent_enriching", label: "Enriching with AI" },
  { phase: "generating_questions", label: "Building your profile draft" },
]

function ExtractingStep({ phases }: { phases: ExtractionPhase[] }) {
  const [visible, setVisible] = useState(0)

  useEffect(() => {
    if (visible >= EXTRACT_PHASES.length) return
    const t = setTimeout(() => setVisible((v) => v + 1), 700)
    return () => clearTimeout(t)
  }, [visible])

  const displayPhases = phases.length > 0
    ? phases.map((p, i) => ({ ...p, index: i }))
    : EXTRACT_PHASES.map((p, i) => ({ ...p, index: i, done: false }))

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-md mx-auto">
      <StepProgress step={3} total={4} />
      <h2 className="text-xl font-heading text-center mb-6">Building your profile</h2>

      <div className="space-y-4">
        {displayPhases.map((p) => (
          <div key={p.phase} className="flex items-center gap-3">
            <div className={`size-2 rounded-full transition-colors duration-300 ${
              p.index < visible ? "bg-primary" : "bg-muted-foreground/20"
            }`} />
            <span className={`text-sm flex-1 ${p.index < visible ? "text-foreground" : "text-muted-foreground/40"}`}>
              {p.label}
            </span>
            {p.index < visible && (
              <motion.span
                initial={{ opacity: 0, scale: 0.5 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-xs font-medium text-primary"
              >
                Done
              </motion.span>
            )}
          </div>
        ))}
      </div>
    </motion.div>
  )
}

// ── STEP 5: Review ──

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
  const sections = buildSections(profile)

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-xl mx-auto">
      <StepProgress step={4} total={4} />
      <h2 className="text-xl font-heading text-center mb-1">Review your profile</h2>
      <p className="text-sm text-muted-foreground text-center mb-6">
        Everything we extracted from your CV. You can edit these later from the dashboard.
      </p>

      {/* Sections */}
      <div className="space-y-2 mb-6">
        {sections.map((s) => (
          <div key={s.key} className="border rounded-lg p-3 flex items-center gap-3">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{s.label}</span>
                {s.status === "gap" && (
                  <Badge variant="outline" className="text-[10px] border-amber-500/30 text-amber-600">missing</Badge>
                )}
              </div>
              <p className="text-xs text-muted-foreground truncate mt-0.5">{s.preview}</p>
            </div>
            {s.status === "complete" && <Check className="size-4 text-green-500 shrink-0" />}
          </div>
        ))}
      </div>

      {/* Deep questions */}
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
                disabled={!answerValue.trim()}
                onClick={() => {
                  onSubmitAnswer(questions.field, answerValue.trim())
                  setAnswerValue("")
                }}
              >
                Save & Continue
              </Button>
              <Button size="sm" variant="ghost" onClick={onSkipQuestions}>Skip all</Button>
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
        <Button variant="outline" className="w-full mb-4" onClick={() => setShowQuestions(true)}>
          Answer {questionsRemaining} question{questionsRemaining !== 1 ? "s" : ""} to improve your profile
        </Button>
      )}

      <Button onClick={onComplete} className="w-full" size="lg" disabled={isCompleting}>
        {isCompleting ? <Spinner className="size-4 mr-2" /> : null}
        Looks good, save and finish
      </Button>
    </motion.div>
  )
}

// ── STEP 6: Complete ──

function CompleteStep() {
  const navigate = useNavigate()

  useEffect(() => {
    const t = setTimeout(() => navigate("/"), 2500)
    return () => clearTimeout(t)
  }, [navigate])

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit" className="max-w-md mx-auto">
      <div className="text-center space-y-4 py-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: "spring", stiffness: 200, damping: 15 }}
          className="text-6xl"
        >
          ✅
        </motion.div>
        <h2 className="text-2xl font-heading">You&apos;re all set</h2>
        <p className="text-muted-foreground">
          Your profile is ready. Redirecting to the dashboard…
        </p>
      </div>
    </motion.div>
  )
}

// ── helpers ──

interface ProfileSection {
  key: string
  label: string
  status: "complete" | "gap" | "empty"
  preview: string
}

function buildSections(profile: Record<string, unknown>): ProfileSection[] {
  const sections: ProfileSection[] = []

  const personal = profile.personal as Record<string, unknown> | undefined
  sections.push({
    key: "name",
    label: "Name",
    status: personal?.name ? "complete" : "gap",
    preview: String(personal?.name || "Not provided"),
  })
  sections.push({
    key: "email",
    label: "Email",
    status: personal?.email ? "complete" : "gap",
    preview: String(personal?.email || "Not provided"),
  })
  sections.push({
    key: "location",
    label: "Location",
    status: personal?.location ? "complete" : "gap",
    preview: String(personal?.location || "Not provided").trim(),
  })

  const prefs = profile.preferences as Record<string, unknown> | undefined
  const roles = prefs?.preferred_roles as string[] | undefined
  sections.push({
    key: "roles",
    label: "Target roles",
    status: roles?.length ? "complete" : "gap",
    preview: roles?.length ? roles.join(", ") : "Not provided",
  })

  const skills = profile.skills as Record<string, unknown> | undefined
  let skillCount = 0
  let skillPreview = ""
  if (skills) {
    const entries: string[] = []
    for (const cat of ["languages", "frameworks", "databases", "devops", "ai_ml", "tools"]) {
      const arr = skills[cat] as unknown[] | undefined
      if (arr) {
        skillCount += arr.length
        entries.push(...arr.map((s) => typeof s === "string" ? s : (s as Record<string, unknown>).name as string || ""))
      }
    }
    skillPreview = entries.slice(0, 5).join(", ") + (entries.length > 5 ? ` +${entries.length - 5} more` : "")
  }
  sections.push({
    key: "skills",
    label: "Skills",
    status: skillCount > 0 ? "complete" : "gap",
    preview: skillPreview || "None found",
  })

  const work = profile.work_experience as Record<string, unknown>[] | undefined
  sections.push({
    key: "experience",
    label: "Work experience",
    status: work?.length ? "complete" : "gap",
    preview: work?.length ? `${work.length} role${work.length > 1 ? "s" : ""} found` : "None found",
  })

  return sections
}

// ── main page ──

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>("welcome")
  const [response, setResponse] = useState<ExtractResponse | null>(null)
  const navigate = useNavigate()

  // Redirect if already complete
  useEffect(() => {
    fetch("/api/onboarding/status")
      .then((r) => r.json())
      .then((data) => {
        if (data.stage === "complete") navigate("/", { replace: true })
      })
  }, [])

  const uploadMutation = useMutation({
    mutationFn: uploadCV,
    onSuccess: (data) => {
      setResponse(data)
      setStep("extracting")
      setTimeout(() => setStep("review"), Math.min(data.extraction_phases.length * 800, 3500))
    },
    onError: (e: Error) => {
      toast.error(e.message)
      setStep("upload")
    },
  })

  const pasteMutation = useMutation({
    mutationFn: extractText,
    onSuccess: (data) => {
      setResponse(data)
      setStep("extracting")
      setTimeout(() => setStep("review"), Math.min(data.extraction_phases.length * 800, 3500))
    },
    onError: (e: Error) => {
      toast.error(e.message)
      setStep("paste")
    },
  })

  const answerMutation = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) => submitAnswer(id, answer),
    onSuccess: (data) => {
      setResponse((prev) => (prev ? { ...prev, ...data } : prev))
      if (!data.next_question) {
        // All questions answered
      }
    },
    onError: () => toast.error("Failed to save answer"),
  })

  const completeMutation = useMutation({
    mutationFn: completeOnboarding,
    onSuccess: () => setStep("complete"),
    onError: () => toast.error("Failed to save profile"),
  })

  const handleFileSubmit = (file: File) => {
    uploadMutation.mutate(file)
  }

  const handlePasteSubmit = (text: string) => {
    pasteMutation.mutate(text)
  }

  return (
    <div className="flex items-start justify-center min-h-[calc(100vh-4rem)] p-6 pt-10">
      <div className="w-full max-w-2xl">
        <AnimatePresence mode="wait">
          {step === "welcome" && (
            <WelcomeStep key="welcome" onNext={() => setStep("source")} />
          )}

          {step === "source" && (
            <SourceStep
              key="source"
              onSelect={(src) => setStep(src)}
            />
          )}

          {step === "upload" && (
            <UploadStep
              key="upload"
              onBack={() => setStep("source")}
              onSubmit={handleFileSubmit}
              isSubmitting={uploadMutation.isPending}
            />
          )}

          {step === "paste" && (
            <PasteStep
              key="paste"
              onBack={() => setStep("source")}
              onSubmit={handlePasteSubmit}
              isSubmitting={pasteMutation.isPending}
            />
          )}

          {step === "extracting" && (
            <ExtractingStep key="extracting" phases={response?.extraction_phases || []} />
          )}

          {step === "review" && response && (
            <ReviewStep
              key="review"
              profile={response.profile}
              questions={response.next_question}
              questionsRemaining={response.questions_remaining}
              onSubmitAnswer={(id, answer) => answerMutation.mutate({ id, answer })}
              onSkipQuestions={() => {}}
              onComplete={() => completeMutation.mutate()}
              isCompleting={completeMutation.isPending}
            />
          )}

          {step === "complete" && <CompleteStep key="complete" />}
        </AnimatePresence>
      </div>
    </div>
  )
}
