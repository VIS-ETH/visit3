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
let csrfToken: string | undefined = undefined;

const backend_url = serverData.backendUrl;

export const getCsrfToken = async () => {
  if (csrfToken) {
    return csrfToken;
  }
  if (csrfPromise) {
    return await csrfPromise;
  } else {
    csrfPromise = axios
      .get(`${backend_url}/csrftoken`, { withCredentials: true })
      .then((res) => {
        csrfToken = res.data.token;
        return res.data.token;
      })
      .finally(() => {
        csrfPromise = undefined;
      });

    return await csrfPromise;
  }
};

export const refreshToken = async () => {
  if (refreshPromise) {
    return await refreshPromise;
  } else {
    refreshPromise = axios
      .post(
        `${backend_url}/auth/refresh`,
        {},
        {
          withCredentials: true,
          headers: {
            "X-CSRF-Token": await getCsrfToken(),
          },
        },
      )
      .then((res) => {
        setToken(res.data.access_token);
        return res.data.access_token;
      })
      .catch(() => {
        clearToken();
        return null;
      })
      .finally(() => {
        refreshPromise = undefined;
      });

    return await refreshPromise;
  }
};

export const setToken = (token: string) => {
  sessionStorage.setItem("token", token);
};

export const getToken = () => {
  return sessionStorage.getItem("token");
};

export const clearToken = () => {
  sessionStorage.removeItem("token");
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

const decodeRoles = () => {
  const token = getToken();
  if (!token) return [];
  const { roles } = jwtDecode<TokenPayload>(token);
  return roles;
};

export const isAdmin = () => {
  try {
    return decodeRoles().includes("admin");
  } catch {
    return false;
  }
};

export const isStaff = () => {
  try {
    return decodeRoles().includes("staff");
  } catch {
    return false;
  }
};

export const isCompany = () => {
  try {
    return decodeRoles().includes("company");
  } catch {
    return false;
  }
};
