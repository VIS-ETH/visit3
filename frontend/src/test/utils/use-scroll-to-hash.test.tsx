import { useEffect, useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { screen, waitFor } from "@testing-library/react";
import { useScrollToHash } from "../../utils/use-scroll-to-hash";
import { renderWithProviders } from "../render";

const INPUT_ID = "late-input";

const LateTarget = () => {
  useScrollToHash();
  const [isReady, setIsReady] = useState(false);
  useEffect(() => {
    const timer = window.setTimeout(() => setIsReady(true), 50);
    return () => window.clearTimeout(timer);
  }, []);
  return isReady ? (
    <div id="late-target">
      <input aria-label={INPUT_ID} id={INPUT_ID} />
    </div>
  ) : null;
};

afterEach(() => {
  vi.restoreAllMocks();
});

describe("scrolling to the linked element", () => {
  it("scrolls to and focuses an element that renders later", async () => {
    const scrollIntoView = vi.spyOn(Element.prototype, "scrollIntoView");
    renderWithProviders(<LateTarget />, { route: "/page#late-target" });

    await waitFor(() => expect(scrollIntoView).toHaveBeenCalledTimes(1));
    expect(scrollIntoView.mock.contexts[0]).toBe(
      document.getElementById("late-target"),
    );
    expect(screen.getByLabelText(INPUT_ID)).toHaveFocus();
  });

  it("does nothing without a hash", async () => {
    const scrollIntoView = vi.spyOn(Element.prototype, "scrollIntoView");
    renderWithProviders(<LateTarget />, { route: "/page" });

    await screen.findByLabelText(INPUT_ID);
    expect(scrollIntoView).not.toHaveBeenCalled();
  });
});
