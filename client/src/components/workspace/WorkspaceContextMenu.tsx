import { useEffect, useRef } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";

interface Props {
  x: number;
  y: number;
  onClose: () => void;
}

export default function WorkspaceContextMenu({ x, y, onClose }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const {
    selectedIds,
    elements,
    clipboard,
    copyElements,
    cutElements,
    pasteElements,
    duplicateElements,
    deleteElements,
    bringToFront,
    bringForward,
    sendBackward,
    sendToBack,
    groupElements,
    ungroupElements,
    toggleLock,
    toggleVisibility,
  } = useWorkspaceStore();

  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("mousedown", handleClick);
    window.addEventListener("keydown", handleKey);
    return () => {
      window.removeEventListener("mousedown", handleClick);
      window.removeEventListener("keydown", handleKey);
    };
  }, [onClose]);

  const hasSelection = selectedIds.length > 0;
  const hasMultiple = selectedIds.length > 1;
  const sel = elements.find((e) => selectedIds.includes(e.id));
  const isFrame = sel?.type === "frame";

  const action = (fn: () => void) => {
    fn();
    onClose();
  };

  return (
    <div
      ref={ref}
      className="ws-context-menu"
      style={{ left: x, top: y }}
    >
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(cutElements)}
      >
        Cut<span className="ws-context-menu-shortcut">Ctrl+X</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(copyElements)}
      >
        Copy<span className="ws-context-menu-shortcut">Ctrl+C</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={clipboard.length === 0}
        onClick={() => action(pasteElements)}
      >
        Paste<span className="ws-context-menu-shortcut">Ctrl+V</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(() => duplicateElements(selectedIds))}
      >
        Duplicate<span className="ws-context-menu-shortcut">Ctrl+D</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(() => deleteElements(selectedIds))}
      >
        Delete<span className="ws-context-menu-shortcut">Del</span>
      </button>

      <div className="ws-context-menu-separator" />

      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(bringToFront)}
      >
        Bring to Front<span className="ws-context-menu-shortcut">Ctrl+]</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(bringForward)}
      >
        Bring Forward<span className="ws-context-menu-shortcut">]</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(sendBackward)}
      >
        Send Backward<span className="ws-context-menu-shortcut">[</span>
      </button>
      <button
        type="button"
        className="ws-context-menu-item"
        disabled={!hasSelection}
        onClick={() => action(sendToBack)}
      >
        Send to Back<span className="ws-context-menu-shortcut">Ctrl+[</span>
      </button>

      <div className="ws-context-menu-separator" />

      {hasMultiple && (
        <button
          type="button"
          className="ws-context-menu-item"
          onClick={() => action(groupElements)}
        >
          Group<span className="ws-context-menu-shortcut">Ctrl+G</span>
        </button>
      )}
      {isFrame && (
        <button
          type="button"
          className="ws-context-menu-item"
          onClick={() => action(ungroupElements)}
        >
          Ungroup
          <span className="ws-context-menu-shortcut">Ctrl+Shift+G</span>
        </button>
      )}

      {sel && (
        <>
          <button
            type="button"
            className="ws-context-menu-item"
            onClick={() => action(() => toggleLock(sel.id))}
          >
            {sel.locked ? "Unlock" : "Lock"}
          </button>
          <button
            type="button"
            className="ws-context-menu-item"
            onClick={() => action(() => toggleVisibility(sel.id))}
          >
            {sel.visible ? "Hide" : "Show"}
          </button>
        </>
      )}
    </div>
  );
}
