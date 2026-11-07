import { useEffect, useRef } from "react";

interface VenueShortcuts {
  cancelDrawing: () => void;
  closePolygon: () => void;
  deleteSelected: () => void;
  hasPendingPolygon: boolean;
}

const isTextEntryFocused = () => {
  const active = document.activeElement;
  if (!(active instanceof HTMLElement)) return false;
  return (
    active.tagName === "INPUT" ||
    active.tagName === "TEXTAREA" ||
    active.isContentEditable
  );
};

export function useVenueShortcuts(shortcuts: VenueShortcuts) {
  const shortcutsRef = useRef(shortcuts);

  useEffect(() => {
    shortcutsRef.current = shortcuts;
  });

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      const current = shortcutsRef.current;
      if (event.key === "Escape") {
        current.cancelDrawing();
        return;
      }
      if (event.key === "Enter" && current.hasPendingPolygon) {
        event.preventDefault();
        current.closePolygon();
        return;
      }
      if (event.key !== "Delete" && event.key !== "Backspace") return;
      if (isTextEntryFocused()) return;
      current.deleteSelected();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
