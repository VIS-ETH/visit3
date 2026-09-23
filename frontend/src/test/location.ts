export interface StubbedLocation {
  navigations: string[];
  restore: () => void;
}

export const stubLocation = (pathname: string): StubbedLocation => {
  const original = Object.getOwnPropertyDescriptor(window, "location");
  const navigations: string[] = [];
  const origin = "http://localhost:3000";

  Object.defineProperty(window, "location", {
    configurable: true,
    value: {
      pathname,
      origin,
      get href() {
        return `${origin}${pathname}`;
      },
      set href(value: string) {
        navigations.push(value);
      },
      assign: (value: string) => navigations.push(value),
      replace: (value: string) => navigations.push(value),
    },
  });

  return {
    navigations,
    restore: () => {
      if (original) Object.defineProperty(window, "location", original);
    },
  };
};
