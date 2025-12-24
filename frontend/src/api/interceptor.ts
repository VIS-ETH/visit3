import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { jwtDecode } from "jwt-decode";
import serverData from "../utils/server-data";

const backend_url = serverData.backendUrl;

const api = axios.create({
  baseURL: backend_url,
  withCredentials: true,
});

const PUBLIC_URLS = ["/users/login", "/users/register", "/users/refresh"];

let refreshPromise: Promise<string | null> | null = null;

const isTokenExpired = (token: string) => {
  try {
    const { exp } = jwtDecode<{ exp: number }>(token);
    return exp < Date.now() / 1000 + 10;
  } catch {
    return true;
  }
};

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    const isPublic = PUBLIC_URLS.some((url) => config.url?.endsWith(url));
    if (isPublic) return config;

    let token = sessionStorage.getItem("token");

    if (!token || isTokenExpired(token)) {
      if (refreshPromise) {
        token = await refreshPromise;
      } else {
        refreshPromise = axios
          .post(`${backend_url}/users/refresh`, {}, { withCredentials: true })
          .then((res) => {
            const newToken = res.data.access_token;
            sessionStorage.setItem("token", newToken);
            return newToken;
          })
          .catch(() => {
            sessionStorage.removeItem("token");
            return null;
          })
          .finally(() => {
            refreshPromise = null;
          });

        token = await refreshPromise;
      }
    }

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
    } else if (!isPublic && !token) {
      window.location.href = "/login";
      return Promise.reject("No valid token");
    }

    return config;
  },
  (error) => Promise.reject(error)
);

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      sessionStorage.removeItem("token");
      window.location.href = "/login";
    }
    return Promise.reject(error);
  }
);

export default api;
