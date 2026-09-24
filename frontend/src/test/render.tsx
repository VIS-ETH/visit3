import type { ReactNode } from "react";
import { MantineProvider } from "@mantine/core";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, type InitialEntry } from "react-router";

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
}

export const renderWithProviders = (
  ui: ReactNode,
  { route = "/", queryClient = createTestQueryClient() }: RenderOptions = {},
) => {
  const user = userEvent.setup();

  const view = render(ui, {
    wrapper: ({ children }) => (
      <MantineProvider env="test">
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={[route]}>{children}</MemoryRouter>
        </QueryClientProvider>
      </MantineProvider>
    ),
  });

  return { ...view, user, queryClient };
};
