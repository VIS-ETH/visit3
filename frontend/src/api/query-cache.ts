import type { QueryClient } from "@tanstack/react-query";

export const resetQueriesForIdentityChange = (queryClient: QueryClient) => {
  queryClient.removeQueries({ type: "inactive" });
  void queryClient.invalidateQueries();
};
