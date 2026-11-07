import { http, HttpResponse } from "msw";
import type { UserResponse } from "../orval/generated/fastAPI.schemas";
import { testBackendUrl } from "./constants";
import { server } from "./server";

export const mockCurrentUser = (user: UserResponse) => {
  server.use(
    http.get(`${testBackendUrl}/api/user/me`, () => HttpResponse.json(user)),
  );
};
