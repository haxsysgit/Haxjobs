import { useState, useCallback, useRef, useEffect } from "react"
import { useNavigate } from "react-router-dom"
import { useMutation, useQuery } from "@tanstack/react-query"
import { motion, AnimatePresence } from "framer-motion"
import { toast } from "sonner"

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { Spinner } from "@/components/ui/spinner"

// ── types ──

type Step = "welcome" | "uploading" | "extracting" | "wizard" | "preview" | "complete"

interface FieldQuestion {
  field: string
  question: string
  type: "text" | "list"
  description: string
  current_value?: string | string[] | null
}

interface WizardState {
  profile: Record<string, unknown>
  next_question: FieldQuestion | null
  questions_remaining: number
  phase: string
}

// ── API helpers ──

const API = "/api"

async function uploadCV(file: File): Promise<WizardState> {
  const form = new FormData()
  form.append("file", file)
  const r = await fetch(`${API}/onboarding/upload`, { method: "POST", body: form })
  if (!r.ok) {
    const e = await r.json().catch(() => ({ detail: "Upload failed" }))
    throw new Error(e.detail || "Upload failed")
  }
  return r.json()
}

async function submitAnswer(questionId: string, answer: string): Promise<WizardState> {
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

// ── components ──

function StepIndicator({ step, total }: { step: number; total: number }) {
  return (
    <div className="flex items-center gap-3 mb-6">
      <Badge variant="secondary" className="text-xs">
        Step {step} of {total}
      </Badge>
      <Progress value={(step / total) * 100} className="flex-1 h-1.5" />
    </div>
  )
}

function WelcomeStep({ onFile }: { onFile: (f: File) => void }) {
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
      <Card className="border-border/60">
        <CardHeader className="text-center pb-4">
          <CardTitle className="text-2xl font-heading">Welcome to HaxJobs</CardTitle>
          <CardDescription className="text-base max-w-sm mx-auto">
            Upload your CV and we&apos;ll build your profile — finding jobs, evaluating fit,
            and generating application packs tailored to you.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
            onClick={() => inputRef.current?.click()}
            className={`border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-all duration-200
              ${dragOver
                ? "border-primary bg-primary/5 scale-[1.02]"
                : "border-muted-foreground/20 hover:border-primary/40 hover:bg-muted/30"
              }`}
          >
            <div className="text-4xl mb-3">📄</div>
            <p className="font-medium text-lg mb-1">
              {dragOver ? "Drop your CV here" : "Drag & drop your CV"}
            </p>
            <p className="text-sm text-muted-foreground">
              PDF or plain text · Max 5 MB ·{" "}
              <span className="text-primary underline underline-offset-2">or browse files</span>
            </p>
          </div>
          <input
            ref={inputRef}
            type="file"
            accept=".pdf,.txt,.md,.json,.docx"
            className="hidden"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (file) onFile(file)
            }}
          />
          <p className="text-xs text-center text-muted-foreground">
            Your data stays local. We extract your profile using AI — nothing is sent anywhere else.
          </p>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function ExtractingStep() {
  const [stage, setStage] = useState(0)
  const messages = [
    "Reading your CV…",
    "Extracting profile details…",
    "Identifying skills & experience…",
    "Analyzing career trajectory…",
    "Almost done…",
  ]

  useEffect(() => {
    const t = setInterval(() => setStage((s) => Math.min(s + 1, messages.length - 1)), 1800)
    return () => clearInterval(t)
  }, [])

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <Card className="border-border/60">
        <CardContent className="flex flex-col items-center py-16 gap-6">
          <Spinner className="size-10" />
          <motion.p
            key={stage}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            className="text-lg font-medium"
          >
            {messages[stage]}
          </motion.p>
          <Progress value={(stage + 1) * 20} className="w-48 h-1.5" />
        </CardContent>
      </Card>
    </motion.div>
  )
}

function QuestionCard({
  question,
  onSubmit,
  isSubmitting,
}: {
  question: FieldQuestion
  onSubmit: (answer: string) => void
  isSubmitting: boolean
}) {
  const [value, setValue] = useState("")

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (value.trim()) onSubmit(value.trim())
  }

  const label = question.field.split(".").pop()?.replace(/_/g, " ") || ""

  return (
    <motion.div
      key={question.field}
      variants={stepVariants}
      initial="enter"
      animate="center"
      exit="exit"
    >
      <Card className="border-border/60">
        <CardHeader className="pb-4">
          <div className="flex items-center gap-2 mb-2">
            <Badge variant="outline" className="text-xs capitalize">
              {question.type === "list" ? "multi-value" : "text"}
            </Badge>
            {question.current_value && (
              <Badge variant="secondary" className="text-xs">
                has current value
              </Badge>
            )}
          </div>
          <CardTitle className="text-xl font-heading">{question.question}</CardTitle>
          <CardDescription>{question.description}</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            {question.type === "list" ? (
              <div className="space-y-2">
                <Textarea
                  value={value}
                  onChange={(e) => setValue(e.target.value)}
                  placeholder="Enter comma-separated values, e.g. Backend Engineer, AI Engineer"
                  rows={3}
                  autoFocus
                  disabled={isSubmitting}
                />
                <p className="text-xs text-muted-foreground">
                  Separate multiple values with commas
                </p>
              </div>
            ) : (
              <Input
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder={`Your ${label}…`}
                autoFocus
                disabled={isSubmitting}
              />
            )}
            <div className="flex justify-end gap-2 pt-2">
              <Button type="submit" disabled={!value.trim() || isSubmitting} className="min-w-[120px]">
                {isSubmitting ? <Spinner className="size-4 mr-2" /> : null}
                Continue
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </motion.div>
  )
}

function PreviewStep({ profile, onSave }: { profile: Record<string, unknown>; onSave: () => void }) {
  const sections = Object.entries(profile).filter(([, v]) => v && (typeof v === "object" || typeof v === "string"))

  return (
    <motion.div variants={stepVariants} initial="enter" animate="center" exit="exit">
      <Card className="border-border/60">
        <CardHeader>
          <CardTitle className="text-xl font-heading">Your Profile</CardTitle>
          <CardDescription>Review what we&apos;ve extracted before saving</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {sections.map(([key, value]) => (
            <div key={key}>
              <h3 className="font-medium text-sm text-muted-foreground uppercase tracking-wide mb-2">
                {key.replace(/_/g, " ")}
              </h3>
              <div className="bg-muted/40 rounded-lg p-3 text-sm">
                {typeof value === "string" ? (
                  <p>{value || <span className="text-muted-foreground italic">Not provided</span>}</p>
                ) : Array.isArray(value) ? (
                  <div className="flex flex-wrap gap-1.5">
                    {value.map((item, i) => (
                      <Badge key={i} variant="secondary">{String(item)}</Badge>
                    ))}
                  </div>
                ) : (
                  <pre className="text-xs whitespace-pre-wrap">{JSON.stringify(value, null, 2)}</pre>
                )}
              </div>
            </div>
          ))}
          <Separator />
          <Button onClick={onSave} className="w-full" size="lg">
            Save Profile & Finish
          </Button>
        </CardContent>
      </Card>
    </motion.div>
  )
}

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

// ── main page ──

export default function OnboardingPage() {
  const [step, setStep] = useState<Step>("welcome")
  const [wizard, setWizard] = useState<WizardState | null>(null)
  const [totalQuestions, setTotalQuestions] = useState(0)
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
      setWizard(data)
      if (data.next_question) {
        // Count total questions for progress
        const base = data.questions_remaining
        setTotalQuestions(base + 1) // current one + remaining
        setStep("wizard")
      } else {
        setStep("preview")
      }
    },
    onError: (e: Error) => {
      toast.error(e.message)
      setStep("welcome")
    },
  })

  const answerMutation = useMutation({
    mutationFn: ({ id, answer }: { id: string; answer: string }) => submitAnswer(id, answer),
    onSuccess: (data) => {
      setWizard(data)
      if (data.next_question) {
        setWizard(data)
      } else if (data.phase === "complete" || !data.next_question) {
        setStep("preview")
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
    setStep("extracting")
    uploadMutation.mutate(file)
  }

  // Redirect if already complete
  if (status?.stage === "complete") {
    navigate("/", { replace: true })
    return null
  }

  const questionsAnswered = totalQuestions - (wizard?.questions_remaining ?? 0)
  const phaseLabel = wizard?.phase === "deep" ? "Deep questions" : "Required fields"

  return (
    <div className="flex items-center justify-center min-h-[calc(100vh-4rem)] p-4">
      <div className="w-full max-w-lg">
        {/* Progress bar — only in wizard step */}
        {step === "wizard" && wizard && (
          <div className="mb-2">
            <StepIndicator step={Math.max(1, questionsAnswered)} total={totalQuestions} />
            {wizard.phase && (
              <p className="text-xs text-muted-foreground text-center -mt-4 mb-4">{phaseLabel}</p>
            )}
          </div>
        )}

        <AnimatePresence mode="wait">
          {step === "welcome" && <WelcomeStep onFile={handleFile} />}
          {step === "extracting" && <ExtractingStep />}
          {step === "wizard" && wizard?.next_question && (
            <div key="wizard-container">
              <QuestionCard
                key={wizard.next_question.field}
                question={wizard.next_question}
                onSubmit={(answer) =>
                  answerMutation.mutate({ id: wizard.next_question!.field, answer })
                }
                isSubmitting={answerMutation.isPending}
              />
              {/* Show remaining count */}
              <p className="text-center text-xs text-muted-foreground mt-4">
                {wizard.questions_remaining} question{wizard.questions_remaining !== 1 ? "s" : ""} remaining
                {wizard.phase === "deep" ? " (personalized)" : ""}
              </p>
            </div>
          )}
          {step === "preview" && wizard && (
            <PreviewStep profile={wizard.profile} onSave={() => completeMutation.mutate()} />
          )}
          {step === "complete" && <CompleteStep />}
        </AnimatePresence>
      </div>
    </div>
  )
}
