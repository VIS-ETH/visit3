import { useLocation } from "react-router";
import {
  clearImpersonation,
  getImpersonatingUserId,
  getImpersonationOrigin,
  setImpersonation,
} from "../../api/utils";
import { useCurrentUser } from "../../context/useCurrentUser";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { getDisplayName } from "../../utils/display";
import { getSafeInternalPath, reloadAt } from "../../utils/navigation";

export const stopImpersonating = () => {
  const origin = getSafeInternalPath(getImpersonationOrigin()) ?? "/";
  clearImpersonation();
  reloadAt(origin);
};

export function useImpersonate() {
  const { user } = useCurrentUser();
  const location = useLocation();
  const canImpersonate = user?.is_admin ?? false;

  const canImpersonateUser = (target: UserResponse) =>
    canImpersonate &&
    !target.is_admin &&
    target.id !== user?.id &&
    getImpersonatingUserId() !== target.id;

  const impersonate = (target: UserResponse) => {
    if (!canImpersonateUser(target)) return;
    setImpersonation(
      target.id,
      getDisplayName(target.first_name, target.last_name, target.email),
      `${location.pathname}${location.search}`,
    );
    reloadAt("/");
  };

  return { canImpersonate, canImpersonateUser, impersonate };
}
