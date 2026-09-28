import { isAxiosError } from "axios";

export const getApiErrorCode = (error: unknown): string | undefined => {
  if (!isAxiosError(error)) return undefined;

  const data: unknown = error.response?.data;
  if (typeof data !== "object" || data === null) return undefined;

  const { code } = data as { code?: unknown };
  return typeof code === "string" ? code : undefined;
};

export const getApiErrorDetails = (
  error: unknown,
): Record<string, unknown> | undefined => {
  if (!isAxiosError(error)) return undefined;

  const data: unknown = error.response?.data;
  if (typeof data !== "object" || data === null) return undefined;

  const { details } = data as { details?: unknown };
  if (typeof details !== "object" || details === null) return undefined;
  return details as Record<string, unknown>;
};

export const getApiErrorStatus = (error: unknown): number | undefined => {
  if (!isAxiosError(error)) return undefined;
  return error.response?.status;
};
