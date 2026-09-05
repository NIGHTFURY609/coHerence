import { useState, useCallback } from "react";
import {
  useWorkspaceStore,
  type ElementType,
  type WorkspaceElement,
} from "@/stores/workspaceStore";
import {
  Square,
  Circle,
  Type,
  ImagePlus,
  SquareDashed,
  Minus,
  Eye,
  EyeOff,
  Lock,
  Unlock,
  Plus,
  Globe,
} from "lucide-react";

const typeIcons: Record<ElementType, typeof Square> = {
  rectangle: Square,
  ellipse: Circle,
  text: Type,
  image: ImagePlus,
  frame: SquareDashed,
  line: Minus,
  website: Globe,
};

export default function WorkspaceSidebar() {
  const {
    elements,
    selectedIds,
    selectElement,
    toggleVisibility,
    toggleLock,
    renameElement,
    addElement,
    reorderElement,
  } = useWorkspaceStore();

  const [editingId, setEditingId] = useState<string | null>(null);
  const [editName, setEditName] = useState("");
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);

  const reversed = [...elements].reverse();

  const startRename = useCallback(
    (el: WorkspaceElement) => {
      setEditingId(el.id);
      setEditName(el.name);
    },
    [],
  );

  const commitRename = useCallback(() => {
    if (editingId && editName.trim()) {
      renameElement(editingId, editName.trim());
    }
    setEditingId(null);
  }, [editingId, editName, renameElement]);

  const handleDragStart = useCallback(
    (e: React.DragEvent, el: WorkspaceElement) => {
      e.dataTransfer.setData("text/plain", el.id);
      e.dataTransfer.effectAllowed = "move";
    },
    [],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent, targetIndex: number) => {
      e.preventDefault();
      const id = e.dataTransfer.getData("text/plain");
      if (id) {
        const actualIndex = elements.length - 1 - targetIndex;
        reorderElement(id, actualIndex);
      }
      setDragOverIndex(null);
    },
    [elements.length, reorderElement],
  );

  const quickAdd = useCallback(
    (type: ElementType) => {
      addElement({
        type,
        x: 100 + Math.random() * 200,
        y: 100 + Math.random() * 200,
      });
    },
    [addElement],
  );

  return (
    <aside className="ws-sidebar">
      <div className="ws-sidebar-header">
        <span>Layers ({elements.length})</span>
        <button
          type="button"
          onClick={() => quickAdd("rectangle")}
          title="Add element"
        >
          <Plus size={14} />
        </button>
      </div>

      <div className="ws-layer-list">
        {reversed.map((el, i) => {
          const Icon = typeIcons[el.type];
          const isSelected = selectedIds.includes(el.id);
          const hiddenClass = !el.visible ? " ws-layer-item--hidden" : "";
          const selectedClass = isSelected ? " ws-layer-item--selected" : "";

          return (
            <div
              key={el.id}
              className={`ws-layer-item${selectedClass}${hiddenClass}`}
              draggable
              onDragStart={(e) => handleDragStart(e, el)}
              onDragOver={(e) => {
                e.preventDefault();
                setDragOverIndex(i);
              }}
              onDragLeave={() => setDragOverIndex(null)}
              onDrop={(e) => handleDrop(e, i)}
              onClick={() => selectElement(el.id)}
              onDoubleClick={() => startRename(el)}
              style={
                dragOverIndex === i
                  ? { borderTopColor: "#D85C45" }
                  : undefined
              }
            >
              <span className="ws-layer-icon">
                <Icon size={14} />
              </span>

              {editingId === el.id ? (
                <input
                  className="ws-layer-name-input"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") commitRename();
                    if (e.key === "Escape") setEditingId(null);
                  }}
                  autoFocus
                  onClick={(e) => e.stopPropagation()}
                />
              ) : (
                <span className="ws-layer-name">{el.name}</span>
              )}

              <div className="ws-layer-actions">
                <button
                  type="button"
                  title={el.visible ? "Hide" : "Show"}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleVisibility(el.id);
                  }}
                >
                  {el.visible ? <Eye size={12} /> : <EyeOff size={12} />}
                </button>
                <button
                  type="button"
                  title={el.locked ? "Unlock" : "Lock"}
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleLock(el.id);
                  }}
                >
                  {el.locked ? <Lock size={12} /> : <Unlock size={12} />}
                </button>
              </div>
            </div>
          );
        })}
      </div>

      <div className="ws-sidebar-footer">
        <button type="button" onClick={() => quickAdd("rectangle")}>
          <Square size={11} /> Rect
        </button>
        <button type="button" onClick={() => quickAdd("ellipse")}>
          <Circle size={11} /> Ellipse
        </button>
        <button type="button" onClick={() => quickAdd("text")}>
          <Type size={11} /> Text
        </button>
        <button type="button" onClick={() => quickAdd("frame")}>
          <SquareDashed size={11} /> Frame
        </button>
        <button type="button" onClick={() => quickAdd("line")}>
          <Minus size={11} /> Line
        </button>
      </div>
    </aside>
  );
}
