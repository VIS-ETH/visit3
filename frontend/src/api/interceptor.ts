import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import serverData from "../utils/server-data";
import {
  clearToken,
  getCsrfToken,
  getToken,
  isTokenExpired,
  refreshToken,
} from "./utils";

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
  (error) => Promise.reject(error),
);

interface ErrorResponse {
  code: string;
  identifier: string;
  message: string;
  statusCode: number;
  redirectTo?: string;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const errorResponse = error?.response?.data as ErrorResponse;
    const status = error?.response?.status;
    const redirectTo = errorResponse?.redirectTo ?? undefined;

    if (status === 401) {
      clearToken();
      window.location.href = "/login";
    } else if (status === 403) {
      if (redirectTo) {
        clearToken();
        window.location.href = "/login";
      } else {
        window.location.href = "/not-allowed";
      }
    }
    console.log(errorResponse);
    return Promise.reject(error);
  },
);

export default api;
