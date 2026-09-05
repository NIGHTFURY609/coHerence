import { useRef, useState, useCallback, type PointerEvent } from "react";
import {
  useWorkspaceStore,
  type WorkspaceElement,
} from "@/stores/workspaceStore";
import { ImagePlus } from "lucide-react";

export default function ElementRenderer({
  element,
}: {
  element: WorkspaceElement;
}) {
  const {
    selectedIds,
    hoveredId,
    activeTool,
    canvas,
    elements,
    selectElement,
    setHoveredId,
    updateElement,
    updateElements,
    pushHistory,
  } = useWorkspaceStore();

  const isSelected = selectedIds.includes(element.id);
  const isHovered = hoveredId === element.id;
  const [isDragging, setIsDragging] = useState(false);
  const dragRef = useRef<{
    startX: number;
    startY: number;
    initialPositions: { id: string; x: number; y: number }[];
  } | null>(null);
  const [isEditing, setIsEditing] = useState(false);
  const textRef = useRef<HTMLDivElement>(null);

  const handlePointerDown = useCallback(
    (e: PointerEvent) => {
      if (activeTool !== "select" || element.locked) return;
      e.stopPropagation();
      (e.currentTarget as HTMLElement).setPointerCapture(e.pointerId);

      const isAlreadySelected = selectedIds.includes(element.id);
      if (!isAlreadySelected) {
        selectElement(element.id, e.shiftKey);
      }
      pushHistory();

      const targets = isAlreadySelected && selectedIds.length > 1 && !e.shiftKey
        ? elements.filter((el) => selectedIds.includes(el.id) && !el.locked)
        : [element];

      dragRef.current = {
        startX: e.clientX,
        startY: e.clientY,
        initialPositions: targets.map((t) => ({ id: t.id, x: t.x, y: t.y })),
      };
      setIsDragging(true);
    },
    [activeTool, element, selectedIds, elements, selectElement, pushHistory],
  );

  const handlePointerMove = useCallback(
    (e: PointerEvent) => {
      if (!isDragging || !dragRef.current) return;
      const dx = (e.clientX - dragRef.current.startX) / canvas.zoom;
      const dy = (e.clientY - dragRef.current.startY) / canvas.zoom;
      if (dragRef.current.initialPositions.length > 1) {
        updateElements(
          dragRef.current.initialPositions.map((p) => ({
            id: p.id,
            changes: { x: Math.round(p.x + dx), y: Math.round(p.y + dy) },
          })),
        );
      } else if (dragRef.current.initialPositions.length === 1) {
        const p = dragRef.current.initialPositions[0];
        updateElement(p.id, {
          x: Math.round(p.x + dx),
          y: Math.round(p.y + dy),
        });
      }
    },
    [isDragging, canvas.zoom, updateElement, updateElements],
  );

  const handlePointerUp = useCallback(() => {
    setIsDragging(false);
    dragRef.current = null;
  }, []);

  const handleDoubleClick = useCallback(() => {
    if (element.type === "text") {
      setIsEditing(true);
      requestAnimationFrame(() => {
        if (textRef.current) {
          textRef.current.focus();
          const sel = window.getSelection();
          const range = document.createRange();
          range.selectNodeContents(textRef.current);
          sel?.removeAllRanges();
          sel?.addRange(range);
        }
      });
    }
  }, [element.type]);

  const handleTextBlur = useCallback(() => {
    setIsEditing(false);
    if (textRef.current) {
      updateElement(element.id, { text: textRef.current.textContent ?? "" });
    }
  }, [element.id, updateElement]);

  const children = elements.filter(
    (e) => e.parentId === element.id && e.visible,
  );

  const selClass = isSelected ? " ws-element--selected" : "";
  const hovClass = isHovered && !isSelected ? " ws-element--hovered" : "";
  const lockClass = element.locked ? " ws-element--locked" : "";

  const wrapperStyle: React.CSSProperties = {
    left: element.x,
    top: element.y,
    width: element.width,
    height: element.height,
    transform: element.rotation ? `rotate(${element.rotation}deg)` : undefined,
    opacity: element.opacity,
  };

  const renderContent = () => {
    switch (element.type) {
      case "rectangle":
        return (
          <div
            style={{
              width: "100%",
              height: "100%",
              background: element.fill,
              opacity: element.fillOpacity,
              borderRadius: element.cornerRadius,
              border:
                element.strokeWidth > 0
                  ? `${element.strokeWidth}px solid ${element.stroke}`
                  : undefined,
            }}
          />
        );

      case "ellipse":
        return (
          <div
            style={{
              width: "100%",
              height: "100%",
              background: element.fill,
              opacity: element.fillOpacity,
              borderRadius: "50%",
              border:
                element.strokeWidth > 0
                  ? `${element.strokeWidth}px solid ${element.stroke}`
                  : undefined,
            }}
          />
        );

      case "text":
        return (
          <div
            ref={textRef}
            className="ws-text-content"
            contentEditable={isEditing}
            suppressContentEditableWarning
            onBlur={handleTextBlur}
            onKeyDown={(e) => {
              if (e.key === "Escape") {
                setIsEditing(false);
                (e.target as HTMLElement).blur();
              }
            }}
            style={{
              fontSize: element.fontSize,
              fontFamily: element.fontFamily,
              fontWeight: element.fontWeight,
              textAlign: element.textAlign,
              lineHeight: element.lineHeight,
              letterSpacing: element.letterSpacing
                ? `${element.letterSpacing}px`
                : undefined,
              color: element.textColor ?? "#173B36",
              cursor: isEditing ? "text" : undefined,
            }}
          >
            {element.text}
          </div>
        );

      case "image":
        return element.src ? (
          <img
            src={element.src}
            alt={element.name}
            draggable={false}
            style={{
              width: "100%",
              height: "100%",
              objectFit: element.objectFit ?? "cover",
              borderRadius: element.cornerRadius,
            }}
          />
        ) : (
          <div className="ws-image-placeholder">
            <ImagePlus size={32} />
          </div>
        );

      case "frame":
        return (
          <>
            <span className="ws-frame-label">{element.name}</span>
            <div
              style={{
                width: "100%",
                height: "100%",
                background: element.fill,
                opacity: element.fillOpacity,
                borderRadius: element.cornerRadius,
                position: "relative",
                overflow: "hidden",
              }}
            >
              {children.map((child) => (
                <ElementRenderer key={child.id} element={child} />
              ))}
            </div>
          </>
        );

      case "line":
        return (
          <svg
            width={element.width || 1}
            height={Math.max(element.height, 2)}
            style={{ overflow: "visible", position: "absolute", top: 0, left: 0 }}
          >
            {element.endArrow && (
              <defs>
                <marker
                  id={`arrow-${element.id}`}
                  markerWidth="8"
                  markerHeight="6"
                  refX="8"
                  refY="3"
                  orient="auto"
                >
                  <path d="M0,0 L8,3 L0,6 Z" fill={element.stroke} />
                </marker>
              </defs>
            )}
            <line
              x1={0}
              y1={element.height / 2 || 1}
              x2={element.x2 ?? element.width}
              y2={(element.y2 ?? 0) + (element.height / 2 || 1)}
              stroke={element.stroke}
              strokeWidth={element.strokeWidth || 2}
              markerEnd={
                element.endArrow ? `url(#arrow-${element.id})` : undefined
              }
            />
          </svg>
        );
    }
  };

  return (
    <div
      className={`ws-element${selClass}${hovClass}${lockClass}`}
      style={wrapperStyle}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onPointerEnter={() => setHoveredId(element.id)}
      onPointerLeave={() => setHoveredId(null)}
      onDoubleClick={handleDoubleClick}
      data-element-id={element.id}
    >
      {renderContent()}
    </div>
  );
}
