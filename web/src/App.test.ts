import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/vue";

import App from "./App.vue";
import { createHaxjobsRouter } from "./router";
import {
  appState,
  clearWorkflowResults,
  initializeAppStatePersistence,
  setDemoOptions,
  setHealthStatus
} from "./state/app-state";
import type { DemoOptionsResponse } from "./types";

const demoOptionsPayload: DemoOptionsResponse = {
  cv_fixtures: [{ id: "Arinze_Agent_engineer_cv.pdf", label: "Agent Engineer CV" }],
  jd_fixtures: [{ id: "60x.txt", label: "60x Agent Engineer JD" }],
  default_cv_fixture: "Arinze_Agent_engineer_cv.pdf",
  default_jd_fixture: "60x.txt",
  modes: ["safe", "stretch", "interview", "ideal"]
};

const successPayload = {
  ok: true,
  metadata: {
    mode: "stretch",
    source: "demo",
    cv_label: "Agent Engineer CV",
    jd_label: "60x Agent Engineer JD"
  },
  fit_summary: {
    score: 72,
    label: "Moderate Fit",
    matched_requirements: 4,
    total_requirements: 6,
    summary: "Deterministic fit summary."
  },
  jd_analysis: {
    role_title: "Backend Engineer",
    section_titles: ["The Role"],
    requirements: [],
    recruiter_concerns: ["Code Quality"],
    required_skills: ["python", "fastapi"],
    desirable_skills: ["vue"]
  },
  candidate_evidence: [],
  evidence_map: [
    {
      requirement_id: "req-1",
      requirement_text: "Strong Python fundamentals",
      section: "The Role",
      importance: "required",
      match_label: "Strong Match",
      claim_label: "Confirmed",
      supporting_evidence: ["Built Python APIs"],
      suggested_safe_wording: "Lead with the existing evidence.",
      risk_warning: null
    },
    {
      requirement_id: "req-2",
      requirement_text: "Production Vue experience",
      section: "The Role",
      importance: "required",
      match_label: "Weak Match",
      claim_label: "Needs User Confirmation",
      supporting_evidence: ["Shipped a small admin panel"],
      suggested_safe_wording: "Frame it as adjacent frontend work.",
      risk_warning: "Do not oversell depth."
    },
    {
      requirement_id: "req-3",
      requirement_text: "Kubernetes ownership",
      section: "The Role",
      importance: "required",
      match_label: "Gap",
      claim_label: "Unsafe Claim",
      supporting_evidence: [],
      suggested_safe_wording: "Handle this as a gap.",
      risk_warning: "No direct evidence found."
    }
  ],
  follow_up_questions: [
    {
      requirement_id: "req-2",
      requirement_text: "Vue experience",
      question: "Can you point to a concrete Vue example?",
      reason: "Needs stronger evidence.",
      priority: "high"
    }
  ],
  warnings: ["One gap needs a tighter example."],
  markdown_report: "# Analysis Metadata"
};

const generatedPackPayload = {
  metadata: {
    mode: "stretch",
    role_title: "Backend Engineer",
    source: "demo",
    aspirational: false,
    follow_up_answer_count: 1,
    unanswered_follow_up_count: 0,
    generated_documents: [
      "tailored_cv_markdown",
      "cover_letter_markdown",
      "interview_notes_markdown",
      "evidence_map_json",
      "application_pack_json"
    ]
  },
  tailored_cv_markdown: "# Tailored CV Draft\n\n## Target Role\nBackend Engineer",
  cover_letter_markdown: "# Cover Letter Draft\n\nDear Hiring Team,",
  interview_notes_markdown: "# Interview Notes\n\n## Strongest Talking Points",
  evidence_map_json: successPayload.evidence_map,
  application_pack_json: {
    documents: {
      tailored_cv_markdown: "# Tailored CV Draft"
    }
  }
};

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

async function renderApp(startPath = "/") {
  window.history.replaceState({}, "", startPath);
  const router = createHaxjobsRouter();
  await router.push(startPath);
  await router.isReady();
  render(App, {
    global: {
      plugins: [router]
    }
  });
  return { router };
}

function resetState(): void {
  clearWorkflowResults();
  appState.selectedMode = "stretch";
  appState.jdText = "";
  appState.userNotes = "";
  appState.demoCvFixture = "";
  appState.demoJdFixture = "";
  appState.demoOptions = null;
  setHealthStatus("connecting", "Checking backend connectivity.", "Waiting for /api/health.");
}

function mockReadyBackend(
  overrides: {
    analyze?: typeof successPayload;
    generate?: typeof generatedPackPayload;
  } = {}
): void {
  const analyzePayload = overrides.analyze ?? successPayload;
  const generatePayload = overrides.generate ?? generatedPackPayload;
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith("/api/health")) {
      return Promise.resolve(jsonResponse({ ok: true, llm_configured: false }));
    }
    if (url.endsWith("/api/demo-options")) {
      return Promise.resolve(jsonResponse(demoOptionsPayload));
    }
    if (url.endsWith("/api/analyze-demo")) {
      return Promise.resolve(jsonResponse(analyzePayload));
    }
    if (url.endsWith("/api/analyze")) {
      return Promise.resolve(jsonResponse(analyzePayload));
    }
    if (url.endsWith("/api/generate-application-pack")) {
      return Promise.resolve(jsonResponse(generatePayload));
    }
    throw new Error(`Unexpected request: ${url} ${init?.method ?? "GET"}`);
  });
}

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    cleanup();
    sessionStorage.clear();
    initializeAppStatePersistence();
    resetState();
    setDemoOptions(demoOptionsPayload);
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
    });
  });

  it("shows the input route without a ready health banner when the backend responds", async () => {
    mockReadyBackend();
    await renderApp("/");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    expect(screen.queryByTestId("health-banner")).not.toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /workflow/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /workspace/i })).toBeInTheDocument();
  });

  it("redirects guarded analysis access back to input when state is missing", async () => {
    mockReadyBackend();
    const { router } = await renderApp("/review");
    await waitFor(() => expect(router.currentRoute.value.path).toBe("/"));
    expect(screen.getByRole("heading", { name: /workspace/i })).toBeInTheDocument();
  });

  it("runs the demo flow and lands on the routed review dashboard", async () => {
    mockReadyBackend();
    const { router } = await renderApp("/");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    await fireEvent.click(screen.getByTestId("demo-button"));
    await waitFor(() => expect(router.currentRoute.value.path).toBe("/review"));
    expect(screen.getByText(/Backend Engineer/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Evidence" })).toBeInTheDocument();
    expect(screen.getAllByText("Kubernetes ownership").length).toBeGreaterThan(0);
  });

  it("blocks interview mode from reaching drafts until required answers are filled", async () => {
    mockReadyBackend({
      analyze: {
        ...successPayload,
        metadata: { ...successPayload.metadata, mode: "interview" }
      }
    });
    const { router } = await renderApp("/");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    await fireEvent.update(screen.getByTestId("mode-select"), "interview");
    await fireEvent.click(screen.getByTestId("demo-button"));
    await waitFor(() => expect(router.currentRoute.value.path).toBe("/review"));
    await router.push("/drafts");
    await waitFor(() => {
      expect(router.currentRoute.value.path).toBe("/review");
      expect(router.currentRoute.value.query.panel).toBe("questions");
    });
    expect(screen.getByRole("heading", { name: "Follow-up Questions" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Drafts" })).toBeDisabled();
  });

  it("renders the draft studio and supports copy plus download actions", async () => {
    mockReadyBackend();
    const clickSpy = vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(() => {});
    const createUrlSpy = vi.fn(() => "blob:test");
    const revokeUrlSpy = vi.fn();
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: createUrlSpy
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: revokeUrlSpy
    });
    const { router } = await renderApp("/");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    await fireEvent.click(screen.getByTestId("demo-button"));
    await waitFor(() => expect(router.currentRoute.value.path).toBe("/review"));
    await fireEvent.click(screen.getByRole("button", { name: "Drafts" }));
    await waitFor(() => expect(router.currentRoute.value.path).toBe("/drafts"));
    await fireEvent.click(screen.getByRole("button", { name: "Generate" }));
    expect(await screen.findByText(/Tailored CV Draft/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "CV" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Cover Letter" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Preview" })).toBeInTheDocument();
    await fireEvent.click(screen.getByRole("button", { name: "Raw" }));
    expect(screen.getByTestId("document-preview")).toHaveTextContent("# Tailored CV Draft");
    await fireEvent.click(screen.getByTestId("copy-output-button"));
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith(
      expect.stringContaining("Tailored CV Draft")
    );
    await fireEvent.click(screen.getByTestId("download-output-button"));
    expect(createUrlSpy).toHaveBeenCalled();
    expect(clickSpy).toHaveBeenCalled();
    expect(revokeUrlSpy).toHaveBeenCalled();
  });

  it("persists workflow state into session storage for refresh recovery", async () => {
    mockReadyBackend();
    await renderApp("/");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    await fireEvent.update(screen.getByTestId("jd-input"), "Stored JD text");
    await fireEvent.update(screen.getByTestId("mode-select"), "ideal");
    await waitFor(() => {
      const persisted = sessionStorage.getItem("haxjobs.app-state.v0.3") ?? "";
      expect(persisted).toContain("Stored JD text");
      expect(persisted).toContain("\"selectedMode\":\"ideal\"");
    });
  });

  it("shows resume actions on the workspace after an analysis exists", async () => {
    mockReadyBackend();
    const { router } = await renderApp("/");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    await fireEvent.click(screen.getByTestId("demo-button"));
    await waitFor(() => expect(router.currentRoute.value.path).toBe("/review"));
    await router.push("/");
    expect(await screen.findByRole("button", { name: "Resume Drafts" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Start Fresh" })).toBeInTheDocument();
  });
});
