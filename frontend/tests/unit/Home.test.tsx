import { render, screen, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import HomePage from "@/app/page";

// Mock next/navigation useRouter
vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

describe("HomePage Component", () => {
  it("renders the primary headline, textarea, and submit button", () => {
    render(<HomePage />);

    expect(screen.getByText(/Tell us where/i)).toBeInTheDocument();
    expect(screen.getByText(/We'll sort the how/i)).toBeInTheDocument();

    const input = screen.getByPlaceholderText(/Find me a combined train and bus route/i);
    expect(input).toBeInTheDocument();

    const submitBtn = screen.getByRole("button", { name: /Plan my trip/i });
    expect(submitBtn).toBeInTheDocument();
    expect(submitBtn).toBeDisabled(); // Disabled when empty
  });

  it("enables the submit button when text is entered", () => {
    render(<HomePage />);

    const input = screen.getByPlaceholderText(/Find me a combined train and bus route/i);
    fireEvent.change(input, { target: { value: "Hyderabad to Chennai Friday" } });

    const submitBtn = screen.getByRole("button", { name: /Plan my trip/i });
    expect(submitBtn).not.toBeDisabled();
  });

  it("populates query when clicking an example chip", () => {
    render(<HomePage />);

    const chips = screen.getAllByRole("button");
    const exampleChip = chips.find((btn) => btn.textContent?.includes("Hyderabad to Chennai"));
    expect(exampleChip).toBeDefined();

    if (exampleChip) {
      fireEvent.click(exampleChip);
      const input = screen.getByPlaceholderText(/Find me a combined train and bus route/i) as HTMLTextAreaElement;
      expect(input.value).toContain("Hyderabad to Chennai");
    }
  });

  it("renders the trust strip guarantees", () => {
    render(<HomePage />);

    expect(screen.getByText("Real timetables")).toBeInTheDocument();
    expect(screen.getByText("No guessing")).toBeInTheDocument();
    expect(screen.getByText("Pan-India scope")).toBeInTheDocument();
  });
});
