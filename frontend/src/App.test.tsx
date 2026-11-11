import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { App } from "./App.tsx";

const summary = {
  id: "plant_weak_assertion_1",
  title: "Read a box label with a weak test",
  requirements: 1,
  requirement_coverage: 1,
  mutation_score: 0,
  finding_count: 1,
};

const detail = {
  id: "plant_weak_assertion_1",
  title: "Read a box label with a weak test",
  requirements: 1,
  requirement_coverage: 1,
  mutation_score: 0,
  mutation_timed_out: 1,
  findings: [
    {
      check: "weak_assertion",
      severity: "medium",
      location: "tests/test_box.py:4",
      explanation: "The test does not contain an assert.",
    },
  ],
};

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
});

describe("App", () => {
  it("shows the empty heading when nothing is stored", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(() => Promise.resolve(jsonResponse([]))),
    );

    render(<App />);

    expect(
      await screen.findByRole("heading", { name: "No tasks stored" }),
    ).toBeTruthy();
  });

  it("shows a loading line while findings are in flight", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        if (String(input) === "/api/tasks") {
          return Promise.resolve(jsonResponse([summary]));
        }
        return new Promise<Response>(() => undefined);
      }),
    );

    render(<App />);
    fireEvent.click(
      await screen.findByRole("button", { name: /plant_weak_assertion_1/ }),
    );

    expect(await screen.findByText("Loading findings.")).toBeTruthy();
  });

  it("shows one stored finding and the timeout count", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: RequestInfo | URL) => {
        const body = String(input) === "/api/tasks" ? [summary] : detail;
        return Promise.resolve(jsonResponse(body));
      }),
    );

    render(<App />);
    fireEvent.click(
      await screen.findByRole("button", { name: /plant_weak_assertion_1/ }),
    );

    expect(await screen.findByText("weak_assertion · medium")).toBeTruthy();
    expect(screen.getByText("tests/test_box.py:4")).toBeTruthy();
    expect(screen.getByText("The test does not contain an assert.")).toBeTruthy();
    expect(screen.getByText(/timed out 1/)).toBeTruthy();
  });
});

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}
