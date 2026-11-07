import { isAxiosError } from "axios";

export const getApiErrorCode = (error: unknown): string | undefined => {
  if (!isAxiosError(error)) return undefined;

  const data: unknown = error.response?.data;
  if (typeof data !== "object" || data === null) return undefined;

  const { code } = data as { code?: unknown };
  return typeof code === "string" ? code : undefined;
};

export const getApiErrorStatus = (error: unknown): number | undefined => {
  if (!isAxiosError(error)) return undefined;
  return error.response?.status;
};

export const getApiFieldErrors = (
  error: unknown,
): { field: string; code: string }[] => {
  if (!isAxiosError(error)) return [];

  const data: unknown = error.response?.data;
  if (typeof data !== "object" || data === null) return [];

  const { fieldErrors } = data as { fieldErrors?: unknown };
  if (!Array.isArray(fieldErrors)) return [];
  return fieldErrors.flatMap((entry: unknown) => {
    if (typeof entry !== "object" || entry === null) return [];
    const { field, code } = entry as { field?: unknown; code?: unknown };
    return typeof field === "string" && typeof code === "string"
      ? [{ field, code }]
      : [];
  });
};

export const INLINE_ERROR_STATUSES: readonly number[] = [
  400, 403, 404, 409, 422,
];

export const inlineErrorRequest = { quietStatuses: INLINE_ERROR_STATUSES };

export const getInlineErrorCode = (error: unknown): string | null => {
  const status = getApiErrorStatus(error);
  if (status === undefined || !INLINE_ERROR_STATUSES.includes(status)) {
    return null;
  }
  return getApiErrorCode(error) ?? "server.error";
};
