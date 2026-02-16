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
  redirectTo: string | undefined;
  statusCode: number;
}

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    const errorResponse = error?.response?.data as ErrorResponse;
    if (error?.response?.status == 401) {
      clearToken();
      window.location.href = "/login";
    } else if (
      errorResponse &&
      errorResponse.statusCode === 307 &&
      errorResponse.redirectTo
    ) {
      window.location.href = errorResponse.redirectTo;
    }
    console.log(errorResponse);
    return Promise.reject(error);
  },
);

export default api;
