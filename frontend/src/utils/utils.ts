import type { TFunction } from "i18next";
import type { ReactNode } from "react";
import { AxiosError } from "axios";

export const safeTranslate = (t: TFunction, n: ReactNode) => {
    typeof n === "string"
    ? t(n)
    : n
}

export const parseBackendErrors = (e: AxiosError<{ detail?: any }>) => {
  const detail = e.response?.data?.detail;
  if (!detail) return {};

  const errors: Record<string, string> = {};

  if (Array.isArray(detail)) {
    detail.forEach((err) => {
      // use 'loc' to map to the field name
      const field = err.loc?.[err.loc.length - 1]; // last part is usually field name
      if (field) errors[field] = err.type || err.msg || "Unknown error";
    });
  } else if (typeof detail === "object") {
    Object.assign(errors, detail);
  }

  return errors;
}
