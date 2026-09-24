import * as jestDomMatchers from "@testing-library/jest-dom/matchers";
import { cleanup } from "@testing-library/react";
import { afterAll, afterEach, beforeAll, expect, vi } from "vitest";
import { notificationsShow, resetNotificationsMock } from "./notifications";
import { server } from "./server";
import { testBackendUrl, testStaticBase, testVisWebsiteUrl } from "./constants";
import "./i18n";

vi.mock("../i18", () => import("./i18n"));

vi.mock("@mantine/notifications", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@mantine/notifications")>()),
  notifications: { show: notificationsShow },
}));

const installBrowserApisMissingFromJsdom = () => {
  Object.defineProperty(HTMLElement.prototype, "innerText", {
    configurable: true,
    get(this: HTMLElement) {
      return this.textContent;
    },
    set(this: HTMLElement, value: string) {
      this.textContent = value;
    },
  });

  window.matchMedia = (query: string) =>
    Object.assign(new EventTarget(), {
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
    }) as MediaQueryList;

  window.ResizeObserver = class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };

  Element.prototype.scrollIntoView = () => {};

  Object.defineProperty(document, "fonts", {
    configurable: true,
    value: Object.assign(new EventTarget(), { ready: Promise.resolve() }),
  });
};

const mountOrgConfig = () => {
  Object.defineProperty(window, "configOptions", {
    configurable: true,
    value: {
      primaryColor: "#1f6feb",
      logo: `${testStaticBase}logo.svg`,
      signet: `${testStaticBase}signet.svg`,
      base: testStaticBase,
    },
  });
};

const mountServerData = () => {
  const element = document.createElement("script");
  element.type = "application/json";
  element.id = "server-data";
  element.textContent = JSON.stringify({
    staticBase: testStaticBase,
    backendUrl: testBackendUrl,
    visWebsiteUrl: testVisWebsiteUrl,
  });
  document.head.appendChild(element);
};

expect.extend(jestDomMatchers);
installBrowserApisMissingFromJsdom();
mountOrgConfig();
mountServerData();

beforeAll(() => {
  server.listen({ onUnhandledRequest: "error" });
});

afterEach(async () => {
  cleanup();
  resetNotificationsMock();
  server.resetHandlers();
  localStorage.clear();
  sessionStorage.clear();
  const { clearCsrfToken } = await import("../api/utils");
  clearCsrfToken();
});

afterAll(() => {
  server.close();
});
