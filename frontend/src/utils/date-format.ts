import i18n from "i18next";

const uiLocale = () => i18n.language;

export function formatDate(
  value: Date | string | null | undefined,
  options: Intl.DateTimeFormatOptions = { dateStyle: "medium" },
) {
  if (!value) return null;
  const date = value instanceof Date ? value : new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  return new Intl.DateTimeFormat(uiLocale(), options).format(date);
}

export const formatDateTime = (value: Date | string | null | undefined) =>
  formatDate(value, { dateStyle: "medium", timeStyle: "short" });
