import { useEffect } from "react";
import { useLocation } from "react-router";

const FOCUSABLE = "input, textarea, select, button";

const reveal = (element: HTMLElement) => {
  element.scrollIntoView({ behavior: "smooth", block: "center" });
  const focusTarget = element.matches(FOCUSABLE)
    ? element
    : element.querySelector<HTMLElement>(FOCUSABLE);
  focusTarget?.focus({ preventScroll: true });
};

export const useScrollToHash = () => {
  const { hash, key } = useLocation();

  useEffect(() => {
    const id = decodeURIComponent(hash.slice(1));
    if (!id) return;
    const present = document.getElementById(id);
    if (present) {
      reveal(present);
      return;
    }
    const observer = new MutationObserver(() => {
      const element = document.getElementById(id);
      if (!element) return;
      observer.disconnect();
      reveal(element);
    });
    observer.observe(document.body, { childList: true, subtree: true });
    return () => observer.disconnect();
  }, [hash, key]);
};
