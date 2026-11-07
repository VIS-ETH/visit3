import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";
import { testBackendUrl } from "./constants";

export const server = setupServer(
  http.get(`${testBackendUrl}/api/csrftoken`, () =>
    HttpResponse.json({ token: "csrf-1" }),
  ),
);
