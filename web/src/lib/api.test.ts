import { buildApiUrl, getApiBaseUrl } from "./api";

describe("api helpers", () => {
  const originalBaseUrl = import.meta.env.VITE_API_BASE_URL;

  afterEach(() => {
    import.meta.env.VITE_API_BASE_URL = originalBaseUrl;
  });

  it("uses a relative API path when no override is configured", () => {
    import.meta.env.VITE_API_BASE_URL = "";
    expect(getApiBaseUrl()).toBe("");
    expect(buildApiUrl("/api/health")).toBe("/api/health");
  });

  it("uses the override URL when VITE_API_BASE_URL is set", () => {
    import.meta.env.VITE_API_BASE_URL = "https://example.test/root/";
    expect(getApiBaseUrl()).toBe("https://example.test/root");
    expect(buildApiUrl("/api/health")).toBe("https://example.test/root/api/health");
  });
});
