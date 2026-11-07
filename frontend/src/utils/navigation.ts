export const COMPANY_PROFILE_PATH = "/company/profile";

export const bookingRequirementElementId = (requirementId: string) =>
  `booking-requirement-${requirementId}`;

const isUnsafeNextCharacter = (character: string) => {
  const code = character.charCodeAt(0);
  return character === "\\" || code < 0x20 || code === 0x7f;
};

export const reloadAt = (path: string) => {
  window.location.assign(path);
};

export function getSafeNextPath(search: string): string | null {
  return getSafeInternalPath(new URLSearchParams(search).get("next"));
}

export function getSafeInternalPath(next: string | null): string | null {
  if (!next?.startsWith("/") || [...next].some(isUnsafeNextCharacter)) {
    return null;
  }

  const origin = window.location.origin;
  const target = new URL(next, origin);

  if (target.origin !== origin) {
    return null;
  }

  return `${target.pathname}${target.search}${target.hash}`;
}

export const LOGIN_PATH = "/login";

export const loginPathWithNext = (next: string) => {
  const safeNext = getSafeInternalPath(next);
  return safeNext && safeNext !== "/"
    ? `${LOGIN_PATH}?next=${encodeURIComponent(safeNext)}`
    : LOGIN_PATH;
};

const LOGIN_NEXT_STORAGE_KEY = "login_next";

export const rememberLoginNext = (next: string | null) => {
  if (next) sessionStorage.setItem(LOGIN_NEXT_STORAGE_KEY, next);
  else sessionStorage.removeItem(LOGIN_NEXT_STORAGE_KEY);
};

export const takeLoginNext = () => {
  const next = getSafeInternalPath(
    sessionStorage.getItem(LOGIN_NEXT_STORAGE_KEY),
  );
  sessionStorage.removeItem(LOGIN_NEXT_STORAGE_KEY);
  return next;
};
