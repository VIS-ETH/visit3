// src/api/axiosInstance.ts
import axios, { AxiosError, type InternalAxiosRequestConfig } from "axios";
import { jwtDecode } from "jwt-decode";
import serverData from "../utils/server-data";
import { redirect } from "react-router";

const backend_url = serverData.backendUrl;

const api = axios.create({
  baseURL: backend_url,
  withCredentials: true,
});

const isTokenExpired = (token: string) => {
  try {
    const { exp } = jwtDecode<{ exp: number }>(token);
    return exp < (Date.now() / 1000) + 10;
  } catch {
    return true;
  }
};

api.interceptors.request.use(
  async (config: InternalAxiosRequestConfig) => {
    let token = sessionStorage.getItem("token");

    if (!token || isTokenExpired(token)) {
      try {
        const response = await axios.post(`${backend_url}/users/refresh`, {}, { withCredentials: true });
        token = response.data.access_token;
        sessionStorage.setItem("token", token!);
      } catch (err) {
        sessionStorage.removeItem("token");
        token = null;
      }
    }

    if (token && config.headers) {
      config.headers.Authorization = `Bearer ${token}`;
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