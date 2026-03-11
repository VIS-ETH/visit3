import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { notifications } from "@mantine/notifications";
import serverData from "../utils/server-data";
import i18n from "../i18";
import { createElement } from "react";
import {
  clearToken,
  getCsrfToken,
  getToken,
  isTokenExpired,
  refreshToken,
} from "./utils";
import { IconX } from "@tabler/icons-react";
const backend_url = serverData.backendUrl;

const api = axios.create({
  baseURL: backend_url,
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

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    config.headers["X-CSRF-Token"] = await getCsrfToken();

    return config;
  },
  (error) => Promise.reject(error)
);

interface ErrorResponse {
  code?: string;
  identifier?: string;
  message?: string;
  statusCode?: number;
  redirectTo?: string;
  detail?: unknown;
}

const getErrorMessage = (errorResponse: ErrorResponse | undefined): string => {
  const detail =
    typeof errorResponse?.detail === "string"
      ? errorResponse.detail
      : undefined;
  const translationKeyCandidates = [errorResponse?.code, detail].filter(
    (value): value is string => Boolean(value)
  );

  const translatedKey = translationKeyCandidates.find((key) =>
    i18n.exists(key)
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

  return i18n.t("server.error");
};

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.code === "ERR_CANCELED") {
      return Promise.reject(error);
    }

    const errorResponse = error?.response?.data as ErrorResponse;
    const status = errorResponse?.statusCode ?? error?.response?.status ?? 0;
    const redirectTo = errorResponse?.redirectTo ?? undefined;

    if (status > 0 && status < 400) {
      return Promise.reject(error);
    }

    if (status === 401) {
      clearToken();
      window.location.href = "/login";
    } else if (redirectTo) {
      window.location.href = redirectTo;
    } else {
      notifications.show({
        color: "red",
        title: i18n.t("error.title"),
        message: getErrorMessage(errorResponse),
        icon: createElement(IconX, { size: 16 }),
        withCloseButton: true,
        withBorder: true,
      });
    }

    return Promise.reject(error);
  }
);

export default api;
