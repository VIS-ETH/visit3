import type { AxiosRequestConfig, AxiosResponse } from "axios";
import api from "./interceptor";

export const customInstance = <T>(
  config: AxiosRequestConfig,
  options?: AxiosRequestConfig,
): Promise<T> => {
  return api({
    ...config,
    ...options,
  }).then((response: AxiosResponse<T>) => response.data);
};

export default customInstance;