export const readSessionBool = (key: string, fallback: boolean) => {
  if (typeof window === "undefined") return fallback;
  const value = window.sessionStorage.getItem(key);
  if (value === null) return fallback;
  return value === "true";
};

export const setSessionBool = (key: string, value: boolean) => {
  if (typeof window === "undefined") return;
  window.sessionStorage.setItem(key, String(value));
};
