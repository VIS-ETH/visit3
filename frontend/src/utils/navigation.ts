export const COMPANY_PROFILE_PATH = "/company/profile";

export const bookingRequirementElementId = (requirementId: string) =>
  `booking-requirement-${requirementId}`;

export function getSafeNextPath(search: string): string | null {
  const next = new URLSearchParams(search).get("next");

  if (!next || !next.startsWith("/") || next.startsWith("//")) {
    return null;
  }

  return next;
}
