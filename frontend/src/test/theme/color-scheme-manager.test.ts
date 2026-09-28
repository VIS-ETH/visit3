import { describe, expect, it } from "vitest";
import type { MantineColorScheme } from "@mantine/core";
import {
  COLOR_SCHEME_KEY,
  createColorSchemeManager,
} from "../../theme/color-scheme-manager";

interface Delivery {
  target: EventTarget;
  event: StorageEvent;
}

const createBrowser = () => {
  const values = new Map<string, string>();
  const targets: EventTarget[] = [];
  const pending: Delivery[] = [];
  const writes: string[] = [];

  const storageFor = (origin: EventTarget): Storage =>
    ({
      getItem: (key: string) => values.get(key) ?? null,
      setItem: (key: string, value: string) => {
        const oldValue = values.get(key) ?? null;
        if (oldValue === value) return;
        values.set(key, value);
        writes.push(value);
        for (const target of targets) {
          if (target === origin) continue;
          pending.push({
            target,
            event: new StorageEvent("storage", {
              key,
              oldValue,
              newValue: value,
            }),
          });
        }
      },
      removeItem: (key: string) => values.delete(key),
      clear: () => values.clear(),
      key: () => null,
      length: 0,
    }) as Storage;

  const openTab = () => {
    const target = new EventTarget();
    targets.push(target);
    const manager = createColorSchemeManager({
      storage: () => storageFor(target),
      events: () => target,
    });
    const tab = {
      scheme: manager.get("auto"),
      changes: 0,
      apply(value: MantineColorScheme) {
        if (value !== tab.scheme) tab.changes += 1;
        tab.scheme = value;
        manager.set(value);
      },
    };
    manager.subscribe((value) => tab.apply(value));
    return tab;
  };

  const deliverInterleaved = (limit = 200) => {
    let delivered = 0;
    while (pending.length > 0 && delivered < limit) {
      const next = pending.shift()!;
      next.target.dispatchEvent(next.event);
      delivered += 1;
    }
    return { delivered, drained: pending.length === 0 };
  };

  return { openTab, deliverInterleaved, writes, values };
};

describe("the color scheme manager", () => {
  it("settles two tabs that change the scheme at the same time", () => {
    const browser = createBrowser();
    const first = browser.openTab();
    const second = browser.openTab();

    first.apply("dark");
    second.apply("light");
    const result = browser.deliverInterleaved();

    expect(result.drained).toBe(true);
    expect(browser.writes).toEqual(["dark", "light"]);
    expect(first.scheme).toBe("light");
    expect(second.scheme).toBe("light");
    expect(first.changes + second.changes).toBeLessThanOrEqual(3);
  });

  it("follows another tab without writing the value back", () => {
    const browser = createBrowser();
    const first = browser.openTab();
    const second = browser.openTab();

    first.apply("dark");
    browser.deliverInterleaved();

    expect(second.scheme).toBe("dark");
    expect(browser.writes).toEqual(["dark"]);
  });

  it("writes a user choice once and skips an unchanged value", () => {
    const browser = createBrowser();
    const tab = browser.openTab();

    tab.apply("dark");
    tab.apply("dark");
    tab.apply("auto");

    expect(browser.writes).toEqual(["dark", "auto"]);
    expect(browser.values.get(COLOR_SCHEME_KEY)).toBe("auto");
  });

  it("starts from the stored scheme and falls back to the default", () => {
    localStorage.setItem(COLOR_SCHEME_KEY, "dark");
    expect(createColorSchemeManager().get("auto")).toBe("dark");

    localStorage.setItem(COLOR_SCHEME_KEY, "sepia");
    expect(createColorSchemeManager().get("auto")).toBe("auto");
    localStorage.removeItem(COLOR_SCHEME_KEY);
  });
});
