export function getFullName(
  firstName?: string | null,
  lastName?: string | null,
) {
  return `${firstName ?? ""} ${lastName ?? ""}`.trim();
}

export function getDisplayName(
  firstName?: string | null,
  lastName?: string | null,
  fallback = "-",
) {
  const fullName = getFullName(firstName, lastName);
  return fullName.length > 0 ? fullName : fallback;
}
