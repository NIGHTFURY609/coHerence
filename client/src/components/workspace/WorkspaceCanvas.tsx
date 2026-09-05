import { useRef, useState, useEffect, useCallback, type PointerEvent, type WheelEvent } from "react";
import { useWorkspaceStore, type WorkspaceElement, type ElementType } from "@/stores/workspaceStore";
import ElementRenderer from "./ElementRenderer";
import TransformHandles from "./TransformHandles";
import SelectionBox from "./SelectionBox";

export default function WorkspaceCanvas() {
  const {
    elements,
    selectedIds,
    activeTool,
    canvas,
    showGrid,
    setCanvasTransform,
    deselectAll,
    selectElements,
    addElement,
    setActiveTool,
  } = useWorkspaceStore();

  const viewportRef = useRef<HTMLDivElement>(null);
  const [isPanning, setIsPanning] = useState(false);
  const panStart = useRef<{ x: number; y: number; panX: number; panY: number } | null>(null);
  const [drawStart, setDrawStart] = useState<{ x: number; y: number } | null>(null);
  const [drawCurrent, setDrawCurrent] = useState<{ x: number; y: number } | null>(null);
  const [marquee, setMarquee] = useState<{ x: number; y: number; w: number; h: number } | null>(null);
  const marqueeStart = useRef<{ x: number; y: number } | null>(null);
  const spaceHeld = useRef(false);

  // Track space key for pan mode
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.code === "Space" && !e.repeat) spaceHeld.current = true;
  }, []);
  const handleKeyUp = useCallback((e: KeyboardEvent) => {
    if (e.code === "Space") spaceHeld.current = false;
  }, []);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    window.addEventListener("keyup", handleKeyUp);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("keyup", handleKeyUp);
    };
  }, [handleKeyDown, handleKeyUp]);

  const screenToCanvas = useCallback(
    (sx: number, sy: number) => {
      const rect = viewportRef.current?.getBoundingClientRect();
      if (!rect) return { x: 0, y: 0 };
      return {
        x: (sx - rect.left - canvas.panX) / canvas.zoom,
        y: (sy - rect.top - canvas.panY) / canvas.zoom,
      };
    },
    [canvas],
  );

  const handleWheel = useCallback(
    (e: WheelEvent) => {
      e.preventDefault();
      const rect = viewportRef.current?.getBoundingClientRect();
      if (!rect) return;

      if (e.ctrlKey || e.metaKey) {
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        const newZoom = Math.min(8, Math.max(0.1, canvas.zoom * factor));
        const mx = e.clientX - rect.left;
        const my = e.clientY - rect.top;
        setCanvasTransform({
          zoom: newZoom,
          panX: mx - ((mx - canvas.panX) / canvas.zoom) * newZoom,
          panY: my - ((my - canvas.panY) / canvas.zoom) * newZoom,
        });
      } else {
        setCanvasTransform({
          panX: canvas.panX - e.deltaX,
          panY: canvas.panY - e.deltaY,
        });
      }
    },
    [canvas, setCanvasTransform],
  );

  const handlePointerDown = useCallback(
    (e: PointerEvent) => {
      if (e.button === 1 || activeTool === "hand" || spaceHeld.current) {
        setIsPanning(true);
        panStart.current = { x: e.clientX, y: e.clientY, panX: canvas.panX, panY: canvas.panY };
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        return;
      }

      const shapeTools: string[] = ["rectangle", "ellipse", "frame", "line", "arrow", "image", "website"];
      if (shapeTools.includes(activeTool) || activeTool === "text") {
        const pt = screenToCanvas(e.clientX, e.clientY);
        setDrawStart(pt);
        setDrawCurrent(pt);
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
        return;
      }

      if (activeTool === "select") {
        const rect = viewportRef.current?.getBoundingClientRect();
        if (!rect) return;
        marqueeStart.current = { x: e.clientX - rect.left, y: e.clientY - rect.top };
        deselectAll();
        (e.target as HTMLElement).setPointerCapture(e.pointerId);
      }
    },
    [activeTool, canvas, screenToCanvas, deselectAll],
  );

  const handlePointerMove = useCallback(
    (e: PointerEvent) => {
      if (isPanning && panStart.current) {
        setCanvasTransform({
          panX: panStart.current.panX + e.clientX - panStart.current.x,
          panY: panStart.current.panY + e.clientY - panStart.current.y,
        });
        return;
      }

      if (drawStart) {
        const pt = screenToCanvas(e.clientX, e.clientY);
        setDrawCurrent(pt);
        return;
      }

      if (marqueeStart.current) {
        const rect = viewportRef.current?.getBoundingClientRect();
        if (!rect) return;
        const cx = e.clientX - rect.left;
        const cy = e.clientY - rect.top;
        setMarquee({
          x: Math.min(marqueeStart.current.x, cx),
          y: Math.min(marqueeStart.current.y, cy),
          w: Math.abs(cx - marqueeStart.current.x),
          h: Math.abs(cy - marqueeStart.current.y),
        });
      }
    },
    [isPanning, drawStart, screenToCanvas, setCanvasTransform],
  );

  const handlePointerUp = useCallback(
    (e: PointerEvent) => {
      if (isPanning) {
        setIsPanning(false);
        panStart.current = null;
        return;
      }

      if (drawStart && drawCurrent) {
        const x = Math.min(drawStart.x, drawCurrent.x);
        const y = Math.min(drawStart.y, drawCurrent.y);
        const w = Math.abs(drawCurrent.x - drawStart.x);
        const h = Math.abs(drawCurrent.y - drawStart.y);

        const isArrow = activeTool === "arrow";
        const isText = activeTool === "text";
        const isImage = activeTool === "image";
        const isWebsite = activeTool === "website";
        const type: ElementType = isArrow
          ? "line"
          : isText
            ? "text"
            : isImage
              ? "image"
              : isWebsite
                ? "website"
                : (activeTool as ElementType);

        if (w > 5 || h > 5 || isText || isImage || isWebsite) {
          const props: Partial<WorkspaceElement> & { type: ElementType } = {
            type,
            x,
            y,
            width: Math.max(w, isText ? 160 : isImage ? 240 : isWebsite ? 680 : 20),
            height: Math.max(h, isText ? 36 : isImage ? 160 : isWebsite ? 440 : 20),
          };
          if (type === "line") {
            props.x2 = drawCurrent.x - x;
            props.y2 = drawCurrent.y - y;
            if (isArrow) props.endArrow = true;
          }
          addElement(props);
          setActiveTool("select");
        }
        setDrawStart(null);
        setDrawCurrent(null);
        return;
      }

      if (marqueeStart.current && marquee) {
        const topLeft = screenToCanvas(
          marquee.x + (viewportRef.current?.getBoundingClientRect().left ?? 0),
          marquee.y + (viewportRef.current?.getBoundingClientRect().top ?? 0),
        );
        const bottomRight = screenToCanvas(
          marquee.x + marquee.w + (viewportRef.current?.getBoundingClientRect().left ?? 0),
          marquee.y + marquee.h + (viewportRef.current?.getBoundingClientRect().top ?? 0),
        );
        const hits = elements.filter(
          (el) =>
            el.visible &&
            !el.locked &&
            el.x < bottomRight.x &&
            el.x + el.width > topLeft.x &&
            el.y < bottomRight.y &&
            el.y + el.height > topLeft.y,
        );
        if (hits.length > 0) selectElements(hits.map((el) => el.id));
      }
      marqueeStart.current = null;
      setMarquee(null);
    },
    [isPanning, drawStart, drawCurrent, marquee, activeTool, elements, addElement, setActiveTool, selectElements, screenToCanvas],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      // 1. Check for URL drop
      const droppedUrl =
        e.dataTransfer.getData("text/uri-list") ||
        e.dataTransfer.getData("text/plain");
      if (
        droppedUrl &&
        (droppedUrl.startsWith("http://") ||
          droppedUrl.startsWith("https://") ||
          droppedUrl.startsWith("/"))
      ) {
        const pt = screenToCanvas(e.clientX, e.clientY);
        let domain = "Website";
        try {
          domain = new URL(droppedUrl, window.location.origin).hostname;
        } catch {}
        addElement({
          type: "website",
          name: domain,
          url: droppedUrl,
          x: Math.round(pt.x),
          y: Math.round(pt.y),
          width: 680,
          height: 440,
        });
        setActiveTool("select");
        return;
      }

      // 2. Check for image file drop
      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        const file = e.dataTransfer.files[0];
        if (file.type.startsWith("image/")) {
          const pt = screenToCanvas(e.clientX, e.clientY);
          const reader = new FileReader();
          reader.onload = (event) => {
            const dataUrl = event.target?.result as string;
            addElement({
              type: "image",
              name: file.name.replace(/\.[^/.]+$/, ""),
              x: pt.x,
              y: pt.y,
              width: 300,
              height: 200,
              src: dataUrl,
            });
            setActiveTool("select");
          };
          reader.readAsDataURL(file);
        }
      }
    },
    [screenToCanvas, addElement, setActiveTool],
  );

  const cursorClass =
    activeTool === "hand" || spaceHeld.current
      ? "ws-canvas-viewport--hand"
      : ["rectangle", "ellipse", "frame", "line", "arrow", "text", "image", "website"].includes(activeTool)
        ? "ws-canvas-viewport--crosshair"
        : "";

  const gridClass = showGrid ? "ws-canvas-viewport--grid" : "";

  const topLevelElements = elements.filter((e) => e.visible && !e.parentId);

  return (
    <div
      ref={viewportRef}
      className={`ws-canvas-viewport ${cursorClass} ${gridClass}`}
      onWheel={handleWheel}
      onPointerDown={handlePointerDown}
      onPointerMove={handlePointerMove}
      onPointerUp={handlePointerUp}
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      style={showGrid ? { backgroundPosition: `${canvas.panX}px ${canvas.panY}px`, backgroundSize: `${20 * canvas.zoom}px ${20 * canvas.zoom}px` } : undefined}
    >
      <div
        className="ws-canvas-transform"
        style={{ transform: `translate(${canvas.panX}px, ${canvas.panY}px) scale(${canvas.zoom})` }}
      >
        {topLevelElements.map((el, index) => (
          <ElementRenderer key={el.id} element={el} zIndex={index + 1} />
        ))}
      </div>

      {/* Draw preview */}
      {drawStart && drawCurrent && (
        <div
          className="ws-selection-marquee"
          style={{
            left: Math.min(drawStart.x, drawCurrent.x) * canvas.zoom + canvas.panX,
            top: Math.min(drawStart.y, drawCurrent.y) * canvas.zoom + canvas.panY,
            width: Math.abs(drawCurrent.x - drawStart.x) * canvas.zoom,
            height: Math.abs(drawCurrent.y - drawStart.y) * canvas.zoom,
          }}
        />
      )}

      <SelectionBox rect={marquee} />
      {selectedIds.length > 0 && <TransformHandles viewportRef={viewportRef} />}
    </div>
  );
}
