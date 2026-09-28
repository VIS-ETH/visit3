import { useEffect } from "react";

export const useWarnOnLeave = (isActive: boolean) => {
  useEffect(() => {
    if (!isActive) return;
    const warn = (event: BeforeUnloadEvent) => event.preventDefault();
    window.addEventListener("beforeunload", warn);
    return () => window.removeEventListener("beforeunload", warn);
  }, [isActive]);
};
