import axios from "axios";
import serverData from "../utils/server-data";
import { jwtDecode } from "jwt-decode";

interface TokenPayload {
  sub: string;
  roles: string[];
  exp: number;
}

let refreshPromise: Promise<string | null> | undefined = undefined;
let csrfPromise: Promise<string> | undefined = undefined;
let csrfRenewPromise: Promise<string> | undefined = undefined;
let csrfToken: string | undefined = undefined;

const backend_url = serverData.backendUrl;

const fetchCsrfToken = async (): Promise<string> => {
  const response = await axios.get(`${backend_url}/api/csrftoken`, {
    withCredentials: true,
  });
  csrfToken = response.data.token;
  return response.data.token;
};

export const getCsrfToken = async () => {
  if (csrfToken) {
    return csrfToken;
  }
  csrfPromise ??= fetchCsrfToken().finally(() => {
    csrfPromise = undefined;
  });

  return await csrfPromise;
};

export const clearCsrfToken = () => {
  csrfToken = undefined;
};

export const renewCsrfToken = async () => {
  csrfToken = undefined;
  csrfRenewPromise ??= fetchCsrfToken().finally(() => {
    csrfRenewPromise = undefined;
  });

  return await csrfRenewPromise;
};

const fetchRefreshedToken = async (): Promise<string | null> => {
  try {
    const response = await axios.post(
      `${backend_url}/api/auth/refresh`,
      {},
      {
        withCredentials: true,
        headers: {
          "X-CSRF-Token": await getCsrfToken(),
        },
      },
    );
    setToken(response.data.access_token);
    return response.data.access_token;
  } catch {
    clearAuthState();
    return null;
  }
};

export const refreshToken = async () => {
  refreshPromise ??= fetchRefreshedToken().finally(() => {
    refreshPromise = undefined;
  });

  return await refreshPromise;
};

const TOKEN_STORAGE_KEY = "token";

const notifyTokenChanged = () => {
  if (typeof window === "undefined") return;
  window.dispatchEvent(new Event("auth-token-changed"));
};

export const setToken = (token: string) => {
  localStorage.setItem(TOKEN_STORAGE_KEY, token);
  notifyTokenChanged();
};

export const getToken = () => {
  return localStorage.getItem(TOKEN_STORAGE_KEY);
};

export const clearToken = () => {
  localStorage.removeItem(TOKEN_STORAGE_KEY);
  notifyTokenChanged();
};

export const subscribeToTokenStorage = (onTokenChanged: () => void) => {
  const handler = (event: StorageEvent) => {
    if (event.key !== null && event.key !== TOKEN_STORAGE_KEY) return;
    if (!getToken()) clearImpersonation();
    onTokenChanged();
  };

  window.addEventListener("storage", handler);
  return () => window.removeEventListener("storage", handler);
};

export const isTokenExpired = () => {
  try {
    const token = getToken();
    if (!token) return true;
    const { exp } = jwtDecode<TokenPayload>(token);
    return exp < Date.now() / 1000 + 10;
  } catch {
    return true;
  }
};

export const getImpersonatingUserId = () =>
  sessionStorage.getItem("impersonating_user_id");

export const getImpersonatingDisplayName = () =>
  sessionStorage.getItem("impersonating_display_name");

export const isImpersonating = () => !!getImpersonatingUserId();

export const setImpersonation = (userId: string, displayName: string) => {
  sessionStorage.setItem("impersonating_user_id", userId);
  sessionStorage.setItem("impersonating_display_name", displayName);
  window.dispatchEvent(new Event("impersonation-changed"));
};

export const clearImpersonation = () => {
  sessionStorage.removeItem("impersonating_user_id");
  sessionStorage.removeItem("impersonating_display_name");
  window.dispatchEvent(new Event("impersonation-changed"));
};

export const clearAuthState = () => {
  clearCsrfToken();
  clearImpersonation();
  clearToken();
};
