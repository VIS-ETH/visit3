export const COMPANY_PROFILE_PATH = "/company/profile";

export const bookingRequirementElementId = (requirementId: string) =>
  `booking-requirement-${requirementId}`;

const isUnsafeNextCharacter = (character: string) => {
  const code = character.charCodeAt(0);
  return character === "\\" || code < 0x20 || code === 0x7f;
};

export function getSafeNextPath(search: string): string | null {
  const next = new URLSearchParams(search).get("next");

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
