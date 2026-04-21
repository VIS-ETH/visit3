import { useContext } from "react";
import { createContext } from "react";
import type { User } from "../orval/generated/fastAPI.schemas";

interface UserContextType {
  user: User | undefined;
  isLoading: boolean;
}

export const UserContext = createContext<UserContextType | undefined>(
  undefined,
);

export function useCurrentUser() {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useCurrentUser must be used within UserProvider");
  }
  return context;
}
