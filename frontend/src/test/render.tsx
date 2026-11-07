import type { ReactNode } from "react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, type InitialEntry } from "react-router";
import { UserProvider } from "../context/UserContext";
import type { UserResponse } from "../orval/generated/fastAPI.schemas";

export const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });

interface RenderOptions {
  route?: InitialEntry;
  queryClient?: QueryClient;
  currentUser?: UserResponse;
}

export const renderWithProviders = (
  ui: ReactNode,
  {
    route = "/",
    queryClient = createTestQueryClient(),
    currentUser,
  }: RenderOptions = {},
) => {
  const user = userEvent.setup();

  const view = render(ui, {
    wrapper: ({ children }) => (
      <MantineProvider env="test">
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[route]}>
            {currentUser ? (
              <UserProvider user={currentUser} isLoading={false}>
                {children}
              </UserProvider>
            ) : (
              children
            )}
          </MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>
    ),
  });

  return { ...view, user, queryClient };
};
