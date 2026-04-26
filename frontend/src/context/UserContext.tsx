import type { ReactNode } from "react";
import type { UserResponse } from "../orval/generated/fastAPI.schemas";
import { UserContext } from "./useCurrentUser";

export function UserProvider({
  children,
  user,
  isLoading,
}: {
  children: ReactNode;
  user: UserResponse | undefined;
  isLoading: boolean;
}) {
  return (
    <UserContext.Provider value={{ user, isLoading }}>
      {children}
    </UserContext.Provider>
  );
}
