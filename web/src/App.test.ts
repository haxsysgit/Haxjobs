import { fireEvent, render, screen, waitFor, within } from "@testing-library/vue";

import App from "./App.vue";

const demoOptionsPayload = {
  cv_fixtures: [
    { id: "Arinze_Agent_engineer_cv.pdf", label: "Agent Engineer CV" }
  ],
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
      priority: "medium"
    }
  ],
  warnings: ["One gap needs a tighter example."],
  markdown_report: "# Analysis Metadata"
};

function makeFile(name = "sample.txt"): File {
  return new File(["CV content"], name, { type: "text/plain" });
}

function uploadFile(file: File): void {
  const input = screen.getByTestId("cv-upload") as HTMLInputElement;
  Object.defineProperty(input, "files", {
    configurable: true,
    value: [file]
  });
  input.dispatchEvent(new Event("change"));
}

function jsonResponse(payload: unknown, status = 200): Response {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

function mockReadyBackend(): void {
  vi.spyOn(globalThis, "fetch").mockImplementation((input, init) => {
    const url = String(input);
    if (url.endsWith("/api/health")) {
      return Promise.resolve(jsonResponse({ ok: true, llm_configured: false }));
    }
    if (url.endsWith("/api/demo-options")) {
      return Promise.resolve(jsonResponse(demoOptionsPayload));
    }
    if (url.endsWith("/api/analyze-demo")) {
      return Promise.resolve(jsonResponse(successPayload));
    }
    if (url.endsWith("/api/analyze")) {
      return Promise.resolve(jsonResponse(successPayload));
    }
    throw new Error(`Unexpected request: ${url} ${init?.method ?? "GET"}`);
  });
}

describe("App", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValue(undefined)
      }
    });
  });

  it("shows a ready health banner when the backend responds", async () => {
    mockReadyBackend();
    render(App);
    expect(await screen.findByText("Backend ready")).toBeInTheDocument();
    expect(screen.getByText(/OPENAI_API_KEY is not loaded/)).toBeInTheDocument();
  });

  it("shows a backend unavailable banner when health checks fail", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("NetworkError"));
    render(App);
    const banner = await screen.findByTestId("health-banner");
    await waitFor(() => {
      expect(within(banner).getByText("Backend unavailable")).toBeInTheDocument();
    });
    expect(within(banner).getByText(/Start `\.\/scripts\/dev\.sh start`/)).toBeInTheDocument();
    expect(screen.getByTestId("analyze-button")).toBeDisabled();
  });

  it("restores JD text and mode from session storage", async () => {
    sessionStorage.setItem("haxjobs.jdText", "Stored JD text");
    sessionStorage.setItem("haxjobs.mode", "ideal");
    mockReadyBackend();
    render(App);
    expect(await screen.findByDisplayValue("Stored JD text")).toBeInTheDocument();
    expect(screen.getByTestId("mode-select")).toHaveValue("ideal");
  });

  it("renders demo analysis results and filters gaps correctly", async () => {
    mockReadyBackend();
    render(App);
    await screen.findByText("Backend ready");
    await waitFor(() => expect(screen.getByTestId("demo-button")).toBeEnabled());
    await fireEvent.click(screen.getByTestId("demo-button"));
    await waitFor(() => {
      expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
      expect(screen.getByText("Evidence Map")).toBeInTheDocument();
    });
    expect(screen.getByText("Strong Python fundamentals")).toBeInTheDocument();
    expect(screen.getByText("Kubernetes ownership")).toBeInTheDocument();
    await fireEvent.click(screen.getByRole("button", { name: "Gaps" }));
    expect(screen.queryByText("Strong Python fundamentals")).not.toBeInTheDocument();
    expect(screen.getByText("Kubernetes ownership")).toBeInTheDocument();
  });

  it("shows a clear backend unavailable message when upload analysis cannot reach the API", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((input) => {
      const url = String(input);
      if (url.endsWith("/api/health")) {
        return Promise.resolve(jsonResponse({ ok: true, llm_configured: true }));
      }
      if (url.endsWith("/api/demo-options")) {
        return Promise.resolve(jsonResponse(demoOptionsPayload));
      }
      if (url.endsWith("/api/analyze")) {
        return Promise.reject(new TypeError("NetworkError"));
      }
      throw new Error(`Unexpected request: ${url}`);
    });
    render(App);
    await screen.findByText("Backend ready");
    uploadFile(makeFile());
    await fireEvent.update(screen.getByTestId("jd-input"), "Backend Engineer JD");
    await fireEvent.click(screen.getByTestId("analyze-button"));
    await waitFor(() => {
      expect(screen.getByRole("alert")).toHaveTextContent(
        "Backend unavailable. Start `./scripts/dev.sh start` and try again."
      );
    });
  });
});
