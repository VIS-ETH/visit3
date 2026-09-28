import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { notifications } from "@mantine/notifications";
import serverData from "../utils/server-data";
import i18n from "../i18";
import { Fragment, createElement } from "react";
import {
  clearAuthState,
  getCsrfToken,
  getImpersonatingUserId,
  getToken,
  isTokenExpired,
  refreshToken,
  renewCsrfToken,
} from "./utils";
import { IconX } from "@tabler/icons-react";
const backend_url = serverData.backendUrl;

const api = axios.create({
  baseURL: `${backend_url}`,
  withCredentials: true,
});

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    let token;

    if (isTokenExpired()) {
      token = await refreshToken();
    } else {
      token = getToken();
    }

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    const impersonatingUserId = getImpersonatingUserId();
    if (impersonatingUserId) {
      config.headers["X-Impersonate-User-Id"] = impersonatingUserId;
    }

    config.headers["X-CSRF-Token"] = await getCsrfToken();

    return config;
  },
  (error) => Promise.reject(error),
);

interface ErrorResponse {
  code?: string;
  identifier?: string;
  message?: string;
  statusCode?: number;
  requestId?: string;
  detail?: unknown;
  fieldErrors?: Array<{
    field?: string;
    code?: string;
    message?: string;
  }>;
}

const parseBlobErrorResponse = async (
  data: unknown,
): Promise<ErrorResponse | undefined> => {
  if (!(data instanceof Blob)) {
    return data as ErrorResponse | undefined;
  }

  if (!data.type.includes("json")) {
    return undefined;
  }

  try {
    return JSON.parse(await data.text()) as ErrorResponse;
  } catch {
    return undefined;
  }
};

const ERROR_CODE_REDIRECTS: Record<string, string> = {
  "error.email_not_confirmed": "/unconfirmed-email",
  "error.not_confirmed": "/unconfirmed-user",
};

const CSRF_ERROR_CODE = "csrf.validation_failed";
const LOGIN_PATH = "/login";

declare module "axios" {
  interface AxiosRequestConfig {
    quietStatuses?: readonly number[];
  }
}

interface RetryableRequestConfig extends InternalAxiosRequestConfig {
  csrfRetried?: boolean;
  authRetried?: boolean;
}

const redirectToLogin = () => {
  if (window.location.pathname !== LOGIN_PATH) {
    window.location.href = LOGIN_PATH;
  }
};

const PAYLOAD_TOO_LARGE = 413;

const isUpload = (request: InternalAxiosRequestConfig | undefined) =>
  request?.data instanceof FormData;

const getUploadErrorMessage = (
  status: number,
  request: InternalAxiosRequestConfig | undefined,
) => {
  if (status === PAYLOAD_TOO_LARGE)
    return i18n.t("error.storage_file_too_large");
  if (status === 0 && isUpload(request)) return i18n.t("error.upload_rejected");
  if (status === 0) return i18n.t("error.network");
  return undefined;
};

const REFERENCE_STYLE = {
  fontSize: "var(--mantine-font-size-xs)",
  marginTop: 4,
  opacity: 0.7,
};

const withReference = (message: string, requestId: string | undefined) =>
  requestId
    ? createElement(
        Fragment,
        null,
        message,
        createElement(
          "div",
          { style: REFERENCE_STYLE },
          `${i18n.t("error.reference")} ${requestId}`,
        ),
      )
    : message;

const getErrorMessage = (errorResponse: ErrorResponse | undefined): string => {
  const firstFieldErrorCode = errorResponse?.fieldErrors?.[0]?.code;
  const detail =
    typeof errorResponse?.detail === "string"
      ? errorResponse.detail
      : undefined;
  const translationKeyCandidates = [
    firstFieldErrorCode,
    errorResponse?.code,
    detail,
  ].filter((value): value is string => Boolean(value));

  const translatedKey = translationKeyCandidates.find((key) =>
    i18n.exists(key),
  );

  if (translatedKey) {
    return i18n.t(translatedKey);
  }

  if (errorResponse?.message) {
    return errorResponse.message;
  }

  if (detail) {
    return detail;
  }

  if (errorResponse?.fieldErrors?.[0]?.message) {
    return errorResponse.fieldErrors[0].message;
  }

  return i18n.t("server.error");
};

api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.code === "ERR_CANCELED") {
      return Promise.reject(error);
    }

    const errorResponse = await parseBlobErrorResponse(error.response?.data);
    const status = errorResponse?.statusCode ?? error.response?.status ?? 0;
    const redirectTo = errorResponse?.code
      ? ERROR_CODE_REDIRECTS[errorResponse.code]
      : undefined;

    if (status > 0 && status < 400) {
      return Promise.reject(error);
    }

    const request = error.config as RetryableRequestConfig | undefined;

    if (
      errorResponse?.code === CSRF_ERROR_CODE &&
      request &&
      !request.csrfRetried
    ) {
      request.csrfRetried = true;
      const renewedCsrfToken = await renewCsrfToken().catch(() => undefined);
      if (renewedCsrfToken) {
        return api(request);
      }
    }

    if (status === 401) {
      if (request && !request.authRetried && getToken()) {
        request.authRetried = true;
        if (await refreshToken()) {
          return api(request);
        }
      }
      clearAuthState();
      redirectToLogin();
    } else if (redirectTo) {
      window.location.href = redirectTo;
    } else if (!request?.quietStatuses?.includes(status)) {
      notifications.show({
        color: "red",
        title: i18n.t("error.title"),
        message: withReference(
          getUploadErrorMessage(status, request) ??
            getErrorMessage(errorResponse),
          errorResponse?.requestId,
        ),
        icon: createElement(IconX, { size: 16 }),
        withCloseButton: true,
        withBorder: true,
      });
    }

    return Promise.reject(error);
  },
);

export default api;
