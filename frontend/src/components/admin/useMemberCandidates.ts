import { useQuery } from "@tanstack/react-query";
import {
  UserFilter,
  type UserResponse,
} from "../../orval/generated/fastAPI.schemas";
import {
  getListUsersQueryKey,
  listUsers,
} from "../../orval/generated/user/user";

const CANDIDATE_LIMIT = 20;
const SCAN_PAGE_SIZE = 100;
const MAX_SCAN_PAGES = 10;

const fetchUnassignedUsers = async (
  query: string | undefined,
  signal: AbortSignal,
) => {
  const found: UserResponse[] = [];
  for (let page = 1; page <= MAX_SCAN_PAGES; page += 1) {
    const result = await listUsers(
      { query, filter: UserFilter.company, page, page_size: SCAN_PAGE_SIZE },
      undefined,
      signal,
    );
    found.push(...result.items.filter((user) => !user.company_id));
    if (
      found.length >= CANDIDATE_LIMIT ||
      page * SCAN_PAGE_SIZE >= result.total
    )
      break;
  }
  return found.slice(0, CANDIDATE_LIMIT);
};

export function useMemberCandidates(search: string, enabled: boolean) {
  const query = search.trim() || undefined;
  return useQuery({
    queryKey: [...getListUsersQueryKey(), "unassigned", query ?? ""],
    queryFn: ({ signal }) => fetchUnassignedUsers(query, signal),
    enabled,
  });
}
