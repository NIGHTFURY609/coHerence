import { useWorkspaceStore } from "@/stores/workspaceStore";

const toolLabels: Record<string, string> = {
  select: "Select",
  hand: "Hand",
  frame: "Frame",
  rectangle: "Rectangle",
  ellipse: "Ellipse",
  line: "Line",
  arrow: "Arrow",
  text: "Text",
  image: "Image",
};

export default function WorkspaceStatusbar() {
  const { elements, selectedIds, activeTool, canvas } = useWorkspaceStore();

  return (
    <footer className="ws-statusbar">
      <div className="ws-statusbar-section">
        <span className="ws-statusbar-dot" />
        <span>{elements.length} elements</span>
        {selectedIds.length > 0 && (
          <span>· {selectedIds.length} selected</span>
        )}
      </div>
      <div className="ws-statusbar-section">
        <span>{toolLabels[activeTool] ?? activeTool}</span>
      </div>
      <div className="ws-statusbar-section">
        <span>{Math.round(canvas.zoom * 100)}%</span>
      </div>
    </footer>
  );
}
