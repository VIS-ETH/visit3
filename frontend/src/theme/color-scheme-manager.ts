import {
  isMantineColorScheme,
  type MantineColorScheme,
  type MantineColorSchemeManager,
} from "@mantine/core";

export const COLOR_SCHEME_KEY = "mantine-color-scheme-value";

interface ColorSchemeManagerOptions {
  storage?: () => Storage;
  events?: () => EventTarget;
}

export const createColorSchemeManager = ({
  storage = () => window.localStorage,
  events = () => window,
}: ColorSchemeManagerOptions = {}): MantineColorSchemeManager => {
  let followedValue: MantineColorScheme | null = null;
  let handleStorage: ((event: Event) => void) | null = null;

  const read = (): MantineColorScheme | null => {
    try {
      const stored = storage().getItem(COLOR_SCHEME_KEY);
      return isMantineColorScheme(stored) ? stored : null;
    } catch {
      return null;
    }
  };

  return {
    get: (defaultValue) => read() ?? defaultValue,
    set: (value) => {
      const isFollowing = followedValue === value;
      followedValue = null;
      if (isFollowing || read() === value) return;
      try {
        storage().setItem(COLOR_SCHEME_KEY, value);
      } catch {
        return;
      }
    },
    subscribe: (onUpdate) => {
      handleStorage = (event) => {
        if ((event as StorageEvent).key !== COLOR_SCHEME_KEY) return;
        const stored = read();
        if (stored === null) return;
        followedValue = stored;
        onUpdate(stored);
        followedValue = null;
      };
      events().addEventListener("storage", handleStorage);
    },
    unsubscribe: () => {
      if (handleStorage) events().removeEventListener("storage", handleStorage);
      handleStorage = null;
    },
    clear: () => {
      try {
        storage().removeItem(COLOR_SCHEME_KEY);
      } catch {
        return;
      }
    },
  };
};

export const colorSchemeManager = createColorSchemeManager();
