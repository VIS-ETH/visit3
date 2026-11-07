import { useState } from "react";

export const useSearchPage = (search: string) => {
  const [state, setState] = useState({ search, page: 1 });
  const page = state.search === search ? state.page : 1;
  const setPage = (next: number) => setState({ search, page: next });
  return [page, setPage] as const;
};
