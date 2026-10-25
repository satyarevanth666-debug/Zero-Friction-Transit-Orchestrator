import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import HomePage from "@/app/page";
import { getPlanSearchUrl } from "@/components/search/SearchHero";

const mockFetch = vi.fn();

const emptyPlanResponse = {
  best_balance: [],
  cheapest: [],
  fastest: [],
  most_reliable: [],
};

describe("HomePage", () => {
  it("normalizes API URLs whether the configured base includes /api or not", () => {
    expect(getPlanSearchUrl("http://localhost:8000/api")).toBe("http://localhost:8000/api/plan/sync");
    expect(getPlanSearchUrl("https://api.example.test")).toBe("https://api.example.test/api/plan/sync");
  });

  beforeEach(() => {
    Object.defineProperty(Element.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    mockFetch.mockReset();
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => emptyPlanResponse,
    });
    vi.stubGlobal("fetch", mockFetch);
  });

  afterEach(() => {
    cleanup();
    vi.unstubAllGlobals();
  });

  it("shows the source-aware route planner", () => {
    render(<HomePage />);

    expect(screen.getByRole("heading", { level: 1, name: /plan across india/i })).toBeInTheDocument();
    expect(screen.getByText("From")).toBeInTheDocument();
    expect(screen.getByText("To")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /verifying gtfs graph|search available routes/i })).toBeInTheDocument();
  });

  it("sends the selected travel date with a route search", async () => {
    const { container } = render(<HomePage />);
    const searchButton = await screen.findByRole("button", { name: /search available routes/i });
    const dateInput = container.querySelector('input[type="date"]');

    expect(dateInput).not.toBeNull();
    fireEvent.change(dateInput as HTMLInputElement, { target: { value: "2026-11-02" } });
    fireEvent.click(searchButton);

    await waitFor(() => expect(mockFetch).toHaveBeenCalledTimes(2));
    const request = JSON.parse(mockFetch.mock.calls[1][1].body);
    expect(request.query).toContain("2026-11-02");
    expect(request.overrides.date).toBe("2026-11-02");
  });

  it("shows an honest empty state instead of sample routes", async () => {
    render(<HomePage />);

    expect(await screen.findByText("No route options to show")).toBeInTheDocument();
    expect(screen.getByText(/no sample or fallback itineraries are shown/i)).toBeInTheDocument();
  });

  it("shows when planner options are available", async () => {
    mockFetch.mockResolvedValue({
      ok: true,
      json: async () => ({ ...emptyPlanResponse, total_itineraries: 5 }),
    });
    render(<HomePage />);

    expect(await screen.findByText(/found 5 itinerary options/i)).toBeInTheDocument();
  });

  it("surfaces backend failures without replacing them with sample data", async () => {
    mockFetch.mockRejectedValue(new Error("Backend unavailable"));
    render(<HomePage />);

    expect(await screen.findByText("Search could not be completed")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Backend unavailable");
    expect(screen.getByText(/no sample or fallback itineraries are shown/i)).toBeInTheDocument();
  });
});
