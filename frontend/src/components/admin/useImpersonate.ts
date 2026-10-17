import { useLocation } from "react-router";
import { setImpersonation } from "../../api/utils";
import { useCurrentUser } from "../../context/useCurrentUser";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { getDisplayName } from "../../utils/display";
import { reloadAt } from "../../utils/navigation";

export function useImpersonate() {
  const { user } = useCurrentUser();
  const location = useLocation();
  const canImpersonate = user?.is_admin ?? false;

  const impersonate = (target: UserResponse) => {
    if (!canImpersonate) return;
    setImpersonation(
      target.id,
      getDisplayName(target.first_name, target.last_name, target.email),
      `${location.pathname}${location.search}`,
    );
    reloadAt("/");
  };

  return { canImpersonate, impersonate };
}
