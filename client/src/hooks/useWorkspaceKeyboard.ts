import { useEffect } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";

export function useWorkspaceKeyboard() {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      )
        return;

      const s = useWorkspaceStore.getState();
      const ctrl = e.ctrlKey || e.metaKey;
      const shift = e.shiftKey;
      const key = e.key.toLowerCase();

      // Tool shortcuts (single key, no modifiers)
      if (!ctrl && !shift) {
        switch (key) {
          case "v":
          case "escape":
            e.preventDefault();
            s.setActiveTool("select");
            return;
          case "h":
            e.preventDefault();
            s.setActiveTool("hand");
            return;
          case "r":
            e.preventDefault();
            s.setActiveTool("rectangle");
            return;
          case "o":
            e.preventDefault();
            s.setActiveTool("ellipse");
            return;
          case "t":
            e.preventDefault();
            s.setActiveTool("text");
            return;
          case "l":
            e.preventDefault();
            s.setActiveTool("line");
            return;
          case "f":
            e.preventDefault();
            s.setActiveTool("frame");
            return;
          case "delete":
          case "backspace":
            e.preventDefault();
            if (s.selectedIds.length > 0) s.deleteElements(s.selectedIds);
            return;
          case "]":
            e.preventDefault();
            s.bringForward();
            return;
          case "[":
            e.preventDefault();
            s.sendBackward();
            return;
        }
      }

      // Ctrl shortcuts
      if (ctrl && !shift) {
        switch (key) {
          case "z":
            e.preventDefault();
            s.undo();
            return;
          case "y":
            e.preventDefault();
            s.redo();
            return;
          case "c":
            e.preventDefault();
            s.copyElements();
            return;
          case "x":
            e.preventDefault();
            s.cutElements();
            return;
          case "v":
            e.preventDefault();
            s.pasteElements();
            return;
          case "d":
            e.preventDefault();
            if (s.selectedIds.length > 0) s.duplicateElements(s.selectedIds);
            return;
          case "a":
            e.preventDefault();
            s.selectAll();
            return;
          case "g":
            e.preventDefault();
            s.groupElements();
            return;
          case "]":
            e.preventDefault();
            s.bringToFront();
            return;
          case "[":
            e.preventDefault();
            s.sendToBack();
            return;
          case "0":
            e.preventDefault();
            s.resetZoom();
            return;
          case "=":
          case "+":
            e.preventDefault();
            s.zoomIn();
            return;
          case "-":
            e.preventDefault();
            s.zoomOut();
            return;
          case "1":
            e.preventDefault();
            s.zoomToFit();
            return;
        }
      }

      // Ctrl+Shift
      if (ctrl && shift) {
        switch (key) {
          case "z":
            e.preventDefault();
            s.redo();
            return;
          case "g":
            e.preventDefault();
            s.ungroupElements();
            return;
        }
      }

      // Arrow key nudge
      if (
        !ctrl &&
        s.selectedIds.length > 0 &&
        ["arrowleft", "arrowright", "arrowup", "arrowdown"].includes(key)
      ) {
        e.preventDefault();
        const nudge = shift ? 10 : 1;
        const dx =
          key === "arrowleft" ? -nudge : key === "arrowright" ? nudge : 0;
        const dy =
          key === "arrowup" ? -nudge : key === "arrowdown" ? nudge : 0;
        s.pushHistory();
        s.updateElements(
          s.selectedIds.map((id) => {
            const el = s.elements.find((e) => e.id === id);
            return {
              id,
              changes: { x: (el?.x ?? 0) + dx, y: (el?.y ?? 0) + dy },
            };
          }),
        );
      }
    };

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);
}
