import { useRef, useCallback, type PointerEvent, type RefObject } from "react";
import { useWorkspaceStore } from "@/stores/workspaceStore";

type HandleDir = "nw" | "n" | "ne" | "e" | "se" | "s" | "sw" | "w";

const HANDLE_SIZE = 8;

const cursors: Record<HandleDir, string> = {
  nw: "nwse-resize",
  n: "ns-resize",
  ne: "nesw-resize",
  e: "ew-resize",
  se: "nwse-resize",
  s: "ns-resize",
  sw: "nesw-resize",
  w: "ew-resize",
};

export default function TransformHandles({
  viewportRef,
}: {
  viewportRef: RefObject<HTMLDivElement | null>;
}) {
  const { elements, selectedIds, canvas, updateElements, pushHistory } =
    useWorkspaceStore();

  const dragRef = useRef<{
    dir: HandleDir;
    startX: number;
    startY: number;
    bounds: { x: number; y: number; w: number; h: number };
    initialElements: { id: string; x: number; y: number; width: number; height: number }[];
  } | null>(null);

  const rotateDragRef = useRef<{
    cx: number;
    cy: number;
    initialRotations: { id: string; rotation: number }[];
    startAngle: number;
  } | null>(null);

  const selected = elements.filter((e) => selectedIds.includes(e.id));
  if (selected.length === 0) return null;

  const minX = Math.min(...selected.map((e) => e.x));
  const minY = Math.min(...selected.map((e) => e.y));
  const maxX = Math.max(...selected.map((e) => e.x + e.width));
  const maxY = Math.max(...selected.map((e) => e.y + e.height));
  const bw = maxX - minX;
  const bh = maxY - minY;

  const toScreen = (cx: number, cy: number) => ({
    x: cx * canvas.zoom + canvas.panX,
    y: cy * canvas.zoom + canvas.panY,
  });

  const tl = toScreen(minX, minY);
  const sw = bw * canvas.zoom;
  const sh = bh * canvas.zoom;

  const rotHandlePos = { x: tl.x + sw / 2, y: tl.y - 22 };

  const handles: { dir: HandleDir; cx: number; cy: number }[] = [
    { dir: "nw", cx: tl.x, cy: tl.y },
    { dir: "n", cx: tl.x + sw / 2, cy: tl.y },
    { dir: "ne", cx: tl.x + sw, cy: tl.y },
    { dir: "e", cx: tl.x + sw, cy: tl.y + sh / 2 },
    { dir: "se", cx: tl.x + sw, cy: tl.y + sh },
    { dir: "s", cx: tl.x + sw / 2, cy: tl.y + sh },
    { dir: "sw", cx: tl.x, cy: tl.y + sh },
    { dir: "w", cx: tl.x, cy: tl.y + sh / 2 },
  ];

  const handlePointerDown = useCallback(
    (e: PointerEvent, dir: HandleDir) => {
      e.stopPropagation();
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      pushHistory();
      dragRef.current = {
        dir,
        startX: e.clientX,
        startY: e.clientY,
        bounds: { x: minX, y: minY, w: bw, h: bh },
        initialElements: selected.map((el) => ({
          id: el.id,
          x: el.x,
          y: el.y,
          width: el.width,
          height: el.height,
        })),
      };
    },
    [pushHistory, minX, minY, bw, bh, selected],
  );

  const handleRotateDown = useCallback(
    (e: PointerEvent) => {
      e.stopPropagation();
      (e.target as HTMLElement).setPointerCapture(e.pointerId);
      pushHistory();
      const centerScreenX = tl.x + sw / 2;
      const centerScreenY = tl.y + sh / 2;
      const startAngle = Math.atan2(e.clientY - centerScreenY, e.clientX - centerScreenX);
      rotateDragRef.current = {
        cx: centerScreenX,
        cy: centerScreenY,
        initialRotations: selected.map((el) => ({ id: el.id, rotation: el.rotation || 0 })),
        startAngle,
      };
    },
    [pushHistory, tl.x, tl.y, sw, sh, selected],
  );

  const handlePointerMove = useCallback(
    (e: PointerEvent) => {
      if (rotateDragRef.current) {
        const { cx, cy, initialRotations, startAngle } = rotateDragRef.current;
        const currentAngle = Math.atan2(e.clientY - cy, e.clientX - cx);
        const deltaDeg = Math.round(((currentAngle - startAngle) * 180) / Math.PI);
        updateElements(
          initialRotations.map((item) => ({
            id: item.id,
            changes: { rotation: (item.rotation + deltaDeg) % 360 },
          })),
        );
        return;
      }

      if (!dragRef.current) return;
      const { dir, startX, startY, bounds, initialElements } = dragRef.current;
      const dx = (e.clientX - startX) / canvas.zoom;
      const dy = (e.clientY - startY) / canvas.zoom;

      let newX = bounds.x;
      let newY = bounds.y;
      let newW = bounds.w;
      let newH = bounds.h;

      if (dir.includes("w")) {
        newX = bounds.x + dx;
        newW = bounds.w - dx;
      }
      if (dir.includes("e")) {
        newW = bounds.w + dx;
      }
      if (dir.includes("n")) {
        newY = bounds.y + dy;
        newH = bounds.h - dy;
      }
      if (dir.includes("s")) {
        newH = bounds.h + dy;
      }

      // Constrain minimum dimension
      if (newW < 8) {
        newW = 8;
        if (dir.includes("w")) newX = bounds.x + bounds.w - 8;
      }
      if (newH < 8) {
        newH = 8;
        if (dir.includes("n")) newY = bounds.y + bounds.h - 8;
      }

      // Shift key locks aspect ratio for corner handles
      if (e.shiftKey && ["nw", "ne", "se", "sw"].includes(dir) && bounds.h > 0) {
        const aspect = bounds.w / bounds.h;
        if (Math.abs(newW - bounds.w) > Math.abs(newH - bounds.h)) {
          newH = newW / aspect;
          if (dir.includes("n")) newY = bounds.y + bounds.h - newH;
        } else {
          newW = newH * aspect;
          if (dir.includes("w")) newX = bounds.x + bounds.w - newW;
        }
      }

      if (initialElements.length === 1) {
        const single = initialElements[0];
        updateElements([
          {
            id: single.id,
            changes: {
              x: Math.round(newX),
              y: Math.round(newY),
              width: Math.max(8, Math.round(newW)),
              height: Math.max(8, Math.round(newH)),
            },
          },
        ]);
      } else {
        const scaleX = bounds.w > 0 ? newW / bounds.w : 1;
        const scaleY = bounds.h > 0 ? newH / bounds.h : 1;
        const updates = initialElements.map((initEl) => ({
          id: initEl.id,
          changes: {
            x: Math.round(newX + (initEl.x - bounds.x) * scaleX),
            y: Math.round(newY + (initEl.y - bounds.y) * scaleY),
            width: Math.max(8, Math.round(initEl.width * scaleX)),
            height: Math.max(8, Math.round(initEl.height * scaleY)),
          },
        }));
        updateElements(updates);
      }
    },
    [canvas.zoom, updateElements],
  );

  const handlePointerUp = useCallback(() => {
    dragRef.current = null;
    rotateDragRef.current = null;
  }, []);

  return (
    <div
      className="ws-transform-overlay"
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
    >
      <svg>
        {/* Selection bounding box */}
        <rect
          x={tl.x}
          y={tl.y}
          width={sw}
          height={sh}
          fill="none"
          stroke="#D85C45"
          strokeWidth={1}
          strokeDasharray="4 2"
          pointerEvents="none"
        />
        {/* Rotation connector line */}
        <line
          x1={tl.x + sw / 2}
          y1={tl.y}
          x2={rotHandlePos.x}
          y2={rotHandlePos.y}
          stroke="#D85C45"
          strokeWidth={1}
          strokeDasharray="2 2"
          pointerEvents="none"
        />
        {/* Rotation circle handle */}
        <circle
          cx={rotHandlePos.x}
          cy={rotHandlePos.y}
          r={4.5}
          className="ws-handle-rotation"
          style={{ cursor: "grab" }}
          onPointerDown={handleRotateDown}
        />
        {/* 8-point resize handles */}
        {handles.map(({ dir, cx, cy }) => (
          <rect
            key={dir}
            className="ws-handle"
            x={cx - HANDLE_SIZE / 2}
            y={cy - HANDLE_SIZE / 2}
            width={HANDLE_SIZE}
            height={HANDLE_SIZE}
            rx={1.5}
            style={{ cursor: cursors[dir] }}
            onPointerDown={(e) => handlePointerDown(e, dir)}
          />
        ))}
      </svg>
    </div>
  );
}
