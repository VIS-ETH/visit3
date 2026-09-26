import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MantineProvider } from "@mantine/core";
import NavbarToggles from "../../components/NavbarToggles";
import {
  COLOR_SCHEME_KEY,
  colorSchemeManager,
} from "../../theme/color-scheme-manager";

const listeners = new Set<(event: MediaQueryListEvent) => void>();
let prefersDark = false;

const schemeChanges: string[] = [];
let observer: MutationObserver;

const currentScheme = () =>
  document.documentElement.getAttribute("data-mantine-color-scheme");

const renderToggles = () =>
  render(
    <MantineProvider
      colorSchemeManager={colorSchemeManager}
      defaultColorScheme="auto"
    >
      <NavbarToggles />
    </MantineProvider>,
  );

const setOsScheme = (dark: boolean) => {
  prefersDark = dark;
  for (const listener of listeners) {
    listener({ matches: dark } as MediaQueryListEvent);
  }
};

const distinctTransitions = () =>
  schemeChanges.filter((value, index) => value !== schemeChanges[index - 1])
    .length;

beforeEach(() => {
  localStorage.removeItem(COLOR_SCHEME_KEY);
  document.documentElement.removeAttribute("data-mantine-color-scheme");
  prefersDark = false;
  listeners.clear();
  vi.spyOn(window, "matchMedia").mockImplementation(
    (query: string) =>
      ({
        get matches() {
          return query.includes("dark") ? prefersDark : false;
        },
        media: query,
        onchange: null,
        addEventListener: (
          _type: string,
          listener: (event: MediaQueryListEvent) => void,
        ) => listeners.add(listener),
        removeEventListener: (
          _type: string,
          listener: (event: MediaQueryListEvent) => void,
        ) => listeners.delete(listener),
        addListener: () => {},
        removeListener: () => {},
        dispatchEvent: () => true,
      }) as unknown as MediaQueryList,
  );
  schemeChanges.length = 0;
  observer = new MutationObserver(() => {
    schemeChanges.push(currentScheme() ?? "");
  });
  observer.observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-mantine-color-scheme"],
  });
});

afterEach(() => {
  observer.disconnect();
});

const flushObserver = () => act(() => Promise.resolve());

describe("the color scheme toggle", () => {
  it("switches to dark with a single change and a single write", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    const user = userEvent.setup();
    const { container } = renderToggles();
    await flushObserver();
    schemeChanges.length = 0;

    const moon = container.querySelector("svg.tabler-icon-moon")!;
    await user.click(moon.closest("button")!);
    await flushObserver();

    expect(currentScheme()).toBe("dark");
    expect(distinctTransitions()).toBe(1);
    expect(
      setItem.mock.calls.filter(([key]) => key === COLOR_SCHEME_KEY),
    ).toEqual([[COLOR_SCHEME_KEY, "dark"]]);
  });

  it("follows the operating system in auto mode without writing", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    renderToggles();
    await flushObserver();
    schemeChanges.length = 0;

    act(() => setOsScheme(true));
    await flushObserver();
    expect(currentScheme()).toBe("dark");

    act(() => setOsScheme(false));
    await flushObserver();

    expect(currentScheme()).toBe("light");
    expect(distinctTransitions()).toBe(2);
    expect(
      setItem.mock.calls.filter(([key]) => key === COLOR_SCHEME_KEY),
    ).toEqual([]);
  });

  it("follows another tab without writing the scheme back", async () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    renderToggles();
    await flushObserver();
    schemeChanges.length = 0;

    localStorage.setItem(COLOR_SCHEME_KEY, "dark");
    setItem.mockClear();
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: COLOR_SCHEME_KEY,
          oldValue: null,
          newValue: "light",
        }),
      );
    });
    await flushObserver();

    expect(currentScheme()).toBe("dark");
    expect(distinctTransitions()).toBe(1);
    expect(setItem).not.toHaveBeenCalled();
  });

  it("keeps the toggle usable after following another tab", async () => {
    const user = userEvent.setup();
    const { container } = renderToggles();
    await flushObserver();

    localStorage.setItem(COLOR_SCHEME_KEY, "dark");
    act(() => {
      window.dispatchEvent(
        new StorageEvent("storage", {
          key: COLOR_SCHEME_KEY,
          newValue: "dark",
        }),
      );
    });
    await flushObserver();

    const sun = container.querySelector("svg.tabler-icon-sun")!;
    await user.click(sun.closest("button")!);
    await flushObserver();

    expect(currentScheme()).toBe("light");
    expect(localStorage.getItem(COLOR_SCHEME_KEY)).toBe("light");
    expect(screen.getAllByRole("button").length).toBeGreaterThan(0);
  });
});
