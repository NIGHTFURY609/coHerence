import { useState, useCallback } from "react";
import WorkspaceCanvas from "@/components/workspace/WorkspaceCanvas";
import WorkspaceToolbar from "@/components/workspace/WorkspaceToolbar";
import WorkspaceSideTab from "@/components/workspace/WorkspaceSideTab";
import WorkspaceStatusbar from "@/components/workspace/WorkspaceStatusbar";
import WorkspaceContextMenu from "@/components/workspace/WorkspaceContextMenu";
import PlaywrightDock from "@/components/workspace/PlaywrightDock";
import { useWorkspaceKeyboard } from "@/hooks/useWorkspaceKeyboard";

export default function Workspace() {
  useWorkspaceKeyboard();
  const [contextMenu, setContextMenu] = useState<{
    x: number;
    y: number;
  } | null>(null);

  const handleContextMenu = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      setContextMenu({ x: e.clientX, y: e.clientY });
    },
    [],
  );

  return (
    <div className="ws-shell" onContextMenu={handleContextMenu}>
      <WorkspaceToolbar />
      <div className="ws-body">
        <WorkspaceCanvas />
        <PlaywrightDock />
        <WorkspaceSideTab />
      </div>
      <WorkspaceStatusbar />
      {contextMenu && (
        <WorkspaceContextMenu
          x={contextMenu.x}
          y={contextMenu.y}
          onClose={() => setContextMenu(null)}
        />
      )}
    </div>
  );
}
