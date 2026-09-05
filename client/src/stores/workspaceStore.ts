/* Workspace store — native React useSyncExternalStore state for the Figma-like canvas editor. */
import { useSyncExternalStore } from "react";
import { nanoid } from "nanoid";

function create<T extends object>(
  initializer: (
    set: (partial: Partial<T> | ((state: T) => Partial<T>)) => void,
    get: () => T,
  ) => T,
) {
  let state: T;
  const listeners = new Set<() => void>();

  const getState = () => state;

  const setState = (partial: Partial<T> | ((state: T) => Partial<T>)) => {
    const next = typeof partial === "function" ? partial(state) : partial;
    if (next && typeof next === "object") {
      state = { ...state, ...next };
      listeners.forEach((l) => l());
    }
  };

  state = initializer(setState, getState);

  function useStore<U = T>(selector?: (s: T) => U): U {
    return useSyncExternalStore(
      (callback) => {
        listeners.add(callback);
        return () => {
          listeners.delete(callback);
        };
      },
      () => (selector ? selector(state) : (state as unknown as U)),
      () => (selector ? selector(state) : (state as unknown as U)),
    );
  }

  useStore.getState = getState;
  useStore.setState = setState;
  useStore.subscribe = (listener: () => void) => {
    listeners.add(listener);
    return () => {
      listeners.delete(listener);
    };
  };

  return useStore;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------
export type ElementType =
  | "rectangle"
  | "ellipse"
  | "text"
  | "image"
  | "frame"
  | "line"
  | "website";

export type ToolType =
  | "select"
  | "hand"
  | "frame"
  | "rectangle"
  | "ellipse"
  | "line"
  | "arrow"
  | "text"
  | "image"
  | "website";

export interface WorkspaceElement {
  id: string;
  type: ElementType;
  name: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  opacity: number;
  visible: boolean;
  locked: boolean;
  parentId: string | null;
  // Fill & Stroke
  fill: string;
  fillOpacity: number;
  stroke: string;
  strokeWidth: number;
  // Border
  cornerRadius: number;
  // Text-specific
  text?: string;
  fontSize?: number;
  fontFamily?: string;
  fontWeight?: number;
  textAlign?: "left" | "center" | "right";
  lineHeight?: number;
  letterSpacing?: number;
  textColor?: string;
  // Image-specific
  src?: string;
  objectFit?: "cover" | "contain" | "fill";
  // Line/Arrow-specific
  x2?: number;
  y2?: number;
  endArrow?: boolean;
  // Website/Embed-specific
  url?: string;
  isInteractive?: boolean;
  useProxy?: boolean;
  viewMode?: "live" | "card";
}

export interface CanvasTransform {
  panX: number;
  panY: number;
  zoom: number;
}

// ---------------------------------------------------------------------------
// Store interface
// ---------------------------------------------------------------------------
export interface WorkspaceState {
  elements: WorkspaceElement[];
  selectedIds: string[];
  hoveredId: string | null;
  activeTool: ToolType;
  canvas: CanvasTransform;
  showGrid: boolean;
  snapEnabled: boolean;

  // History
  past: WorkspaceElement[][];
  future: WorkspaceElement[][];

  // Clipboard
  clipboard: WorkspaceElement[];

  // --- Element CRUD ---
  addElement: (
    partial: Partial<WorkspaceElement> & { type: ElementType },
  ) => string;
  updateElement: (id: string, updates: Partial<WorkspaceElement>) => void;
  updateElements: (
    updates: { id: string; changes: Partial<WorkspaceElement> }[],
  ) => void;
  deleteElements: (ids: string[]) => void;
  duplicateElements: (ids: string[]) => string[];

  // --- Selection ---
  selectElement: (id: string, addToSelection?: boolean) => void;
  selectElements: (ids: string[]) => void;
  selectAll: () => void;
  deselectAll: () => void;
  setHoveredId: (id: string | null) => void;

  // --- Tool ---
  setActiveTool: (tool: ToolType) => void;

  // --- Canvas ---
  setCanvasTransform: (t: Partial<CanvasTransform>) => void;
  zoomIn: () => void;
  zoomOut: () => void;
  zoomToFit: () => void;
  resetZoom: () => void;

  // --- Layer ordering ---
  bringToFront: () => void;
  sendToBack: () => void;
  bringForward: () => void;
  sendBackward: () => void;
  reorderElement: (id: string, newIndex: number) => void;

  // --- Grouping ---
  groupElements: () => void;
  ungroupElements: () => void;

  // --- Alignment ---
  alignElements: (
    alignment:
      | "left"
      | "right"
      | "top"
      | "bottom"
      | "centerH"
      | "centerV",
  ) => void;
  distributeElements: (direction: "horizontal" | "vertical") => void;

  // --- History ---
  undo: () => void;
  redo: () => void;
  pushHistory: () => void;

  // --- Toggle UI ---
  toggleGrid: () => void;
  toggleSnap: () => void;

  // --- Lock / Visibility ---
  toggleLock: (id: string) => void;
  toggleVisibility: (id: string) => void;

  // --- Clipboard ---
  copyElements: () => void;
  cutElements: () => void;
  pasteElements: () => void;

  // --- Rename ---
  renameElement: (id: string, name: string) => void;

  // --- Bulk & Templates ---
  loadElements: (elements: WorkspaceElement[]) => void;
  clearAll: () => void;
  resetToTemplate: () => void;
}

// ---------------------------------------------------------------------------
// Defaults for new elements
// ---------------------------------------------------------------------------
const DEFAULTS: Record<ElementType, Partial<WorkspaceElement>> = {
  rectangle: {
    width: 200,
    height: 150,
    fill: "#C9D9B2",
    stroke: "transparent",
    strokeWidth: 0,
    cornerRadius: 0,
    opacity: 1,
    fillOpacity: 1,
  },
  ellipse: {
    width: 160,
    height: 160,
    fill: "#D85C45",
    stroke: "transparent",
    strokeWidth: 0,
    cornerRadius: 0,
    opacity: 1,
    fillOpacity: 1,
  },
  text: {
    width: 200,
    height: 40,
    fill: "transparent",
    stroke: "transparent",
    strokeWidth: 0,
    cornerRadius: 0,
    opacity: 1,
    fillOpacity: 0,
    text: "Type something",
    fontSize: 18,
    fontFamily: "Manrope",
    fontWeight: 500,
    textAlign: "left",
    lineHeight: 1.5,
    letterSpacing: 0,
    textColor: "#173B36",
  },
  image: {
    width: 300,
    height: 200,
    fill: "#eee4d5",
    stroke: "transparent",
    strokeWidth: 0,
    cornerRadius: 0,
    opacity: 1,
    fillOpacity: 1,
    objectFit: "cover",
  },
  frame: {
    width: 400,
    height: 300,
    fill: "#FFFFFF",
    stroke: "transparent",
    strokeWidth: 0,
    cornerRadius: 0,
    opacity: 1,
    fillOpacity: 1,
  },
  line: {
    width: 200,
    height: 0,
    fill: "transparent",
    stroke: "#173B36",
    strokeWidth: 2,
    cornerRadius: 0,
    opacity: 1,
    fillOpacity: 0,
    x2: 200,
    y2: 0,
    endArrow: false,
  },
  website: {
    width: 640,
    height: 440,
    fill: "#1e1e1e",
    stroke: "rgba(255,255,255,0.15)",
    strokeWidth: 1,
    cornerRadius: 8,
    opacity: 1,
    fillOpacity: 1,
    url: "https://wikipedia.org",
    isInteractive: false,
    useProxy: true,
    viewMode: "live",
  },
};

function nameForType(type: ElementType, elements: WorkspaceElement[]): string {
  const count = elements.filter((e) => e.type === type).length + 1;
  const labels: Record<ElementType, string> = {
    rectangle: "Rectangle",
    ellipse: "Ellipse",
    text: "Text",
    image: "Image",
    frame: "Frame",
    line: "Line",
    website: "Website",
  };
  return `${labels[type]} ${count}`;
}

const INITIAL_ELEMENTS: WorkspaceElement[] = [];

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------
export const useWorkspaceStore = create<WorkspaceState>((set, get) => ({
  elements: INITIAL_ELEMENTS,
  selectedIds: [],
  hoveredId: null,
  activeTool: "select",
  canvas: { panX: 40, panY: 40, zoom: 0.85 },
  showGrid: true,
  snapEnabled: true,
  past: [],
  future: [],
  clipboard: [],

  // ------ Element CRUD ------
  addElement: (partial) => {
    const state = get();
    const id = nanoid(10);
    const defaults = DEFAULTS[partial.type] ?? {};
    const base: WorkspaceElement = {
      id,
      type: partial.type,
      name: nameForType(partial.type, state.elements),
      x: 100,
      y: 100,
      width: 200,
      height: 150,
      rotation: 0,
      opacity: 1,
      visible: true,
      locked: false,
      parentId: null,
      fill: "#C9D9B2",
      fillOpacity: 1,
      stroke: "transparent",
      strokeWidth: 0,
      cornerRadius: 0,
    };
    const el: WorkspaceElement = Object.assign(
      base,
      defaults,
      partial,
      { id, name: partial.name ?? nameForType(partial.type, state.elements) },
    );
    set((s) => ({
      elements: [...s.elements, el],
      selectedIds: [id],
      past: [...s.past, s.elements],
      future: [],
    }));
    return id;
  },

  updateElement: (id, updates) => {
    set((s) => ({
      elements: s.elements.map((e) =>
        e.id === id ? { ...e, ...updates } : e,
      ),
    }));
  },

  updateElements: (updates) => {
    set((s) => {
      const map = new Map(updates.map((u) => [u.id, u.changes]));
      return {
        elements: s.elements.map((e) =>
          map.has(e.id) ? { ...e, ...map.get(e.id) } : e,
        ),
      };
    });
  },

  deleteElements: (ids) => {
    const s = get();
    set({
      elements: s.elements.filter((e) => !ids.includes(e.id)),
      selectedIds: s.selectedIds.filter((id) => !ids.includes(id)),
      past: [...s.past, s.elements],
      future: [],
    });
  },

  duplicateElements: (ids) => {
    const s = get();
    const toDuplicate = s.elements.filter((e) => ids.includes(e.id));
    const newEls = toDuplicate.map((e) => ({
      ...e,
      id: nanoid(10),
      name: `${e.name} copy`,
      x: e.x + 20,
      y: e.y + 20,
    }));
    const newIds = newEls.map((e) => e.id);
    set({
      elements: [...s.elements, ...newEls],
      selectedIds: newIds,
      past: [...s.past, s.elements],
      future: [],
    });
    return newIds;
  },

  // ------ Selection ------
  selectElement: (id, addToSelection = false) => {
    set((s) => ({
      selectedIds: addToSelection
        ? s.selectedIds.includes(id)
          ? s.selectedIds.filter((sid) => sid !== id)
          : [...s.selectedIds, id]
        : [id],
    }));
  },

  selectElements: (ids) => set({ selectedIds: ids }),

  selectAll: () =>
    set((s) => ({
      selectedIds: s.elements
        .filter((e) => !e.locked && e.visible)
        .map((e) => e.id),
    })),

  deselectAll: () => set({ selectedIds: [] }),

  setHoveredId: (id) => set({ hoveredId: id }),

  // ------ Tool ------
  setActiveTool: (tool) => set({ activeTool: tool }),

  // ------ Canvas ------
  setCanvasTransform: (t) =>
    set((s) => ({ canvas: { ...s.canvas, ...t } })),

  zoomIn: () =>
    set((s) => ({
      canvas: { ...s.canvas, zoom: Math.min(8, s.canvas.zoom * 1.2) },
    })),

  zoomOut: () =>
    set((s) => ({
      canvas: { ...s.canvas, zoom: Math.max(0.1, s.canvas.zoom / 1.2) },
    })),

  zoomToFit: () => {
    const s = get();
    if (s.elements.length === 0) {
      set({ canvas: { panX: 0, panY: 0, zoom: 1 } });
      return;
    }
    const xs = s.elements.map((e) => e.x);
    const ys = s.elements.map((e) => e.y);
    const x2s = s.elements.map((e) => e.x + e.width);
    const y2s = s.elements.map((e) => e.y + e.height);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys);
    const maxX = Math.max(...x2s);
    const maxY = Math.max(...y2s);
    const contentW = maxX - minX + 100;
    const contentH = maxY - minY + 100;
    const zoom = Math.min(1, 800 / contentW, 600 / contentH);
    set({
      canvas: {
        panX: -(minX - 50) * zoom,
        panY: -(minY - 50) * zoom,
        zoom,
      },
    });
  },

  resetZoom: () =>
    set({ canvas: { panX: 0, panY: 0, zoom: 1 } }),

  // ------ Layer ordering ------
  bringToFront: () => {
    const s = get();
    const selected = s.elements.filter((e) => s.selectedIds.includes(e.id));
    const rest = s.elements.filter((e) => !s.selectedIds.includes(e.id));
    set({ elements: [...rest, ...selected], past: [...s.past, s.elements], future: [] });
  },

  sendToBack: () => {
    const s = get();
    const selected = s.elements.filter((e) => s.selectedIds.includes(e.id));
    const rest = s.elements.filter((e) => !s.selectedIds.includes(e.id));
    set({ elements: [...selected, ...rest], past: [...s.past, s.elements], future: [] });
  },

  bringForward: () => {
    const s = get();
    const els = [...s.elements];
    for (const id of s.selectedIds) {
      const i = els.findIndex((e) => e.id === id);
      if (i < els.length - 1) {
        [els[i], els[i + 1]] = [els[i + 1], els[i]];
      }
    }
    set({ elements: els, past: [...s.past, s.elements], future: [] });
  },

  sendBackward: () => {
    const s = get();
    const els = [...s.elements];
    for (const id of [...s.selectedIds].reverse()) {
      const i = els.findIndex((e) => e.id === id);
      if (i > 0) {
        [els[i], els[i - 1]] = [els[i - 1], els[i]];
      }
    }
    set({ elements: els, past: [...s.past, s.elements], future: [] });
  },

  reorderElement: (id, newIndex) => {
    const s = get();
    const els = s.elements.filter((e) => e.id !== id);
    const el = s.elements.find((e) => e.id === id);
    if (!el) return;
    els.splice(newIndex, 0, el);
    set({ elements: els, past: [...s.past, s.elements], future: [] });
  },

  // ------ Grouping ------
  groupElements: () => {
    const s = get();
    if (s.selectedIds.length < 2) return;
    const selected = s.elements.filter((e) => s.selectedIds.includes(e.id));
    const xs = selected.map((e) => e.x);
    const ys = selected.map((e) => e.y);
    const x2s = selected.map((e) => e.x + e.width);
    const y2s = selected.map((e) => e.y + e.height);
    const frameId = nanoid(10);
    const minX = Math.min(...xs);
    const minY = Math.min(...ys);
    const frame: WorkspaceElement = {
      id: frameId,
      type: "frame",
      name: nameForType("frame", s.elements),
      x: minX,
      y: minY,
      width: Math.max(...x2s) - minX,
      height: Math.max(...y2s) - minY,
      rotation: 0,
      opacity: 1,
      visible: true,
      locked: false,
      parentId: null,
      fill: "transparent",
      fillOpacity: 0,
      stroke: "transparent",
      strokeWidth: 0,
      cornerRadius: 0,
    };
    const updated = s.elements.map((e) =>
      s.selectedIds.includes(e.id)
        ? { ...e, parentId: frameId, x: e.x - minX, y: e.y - minY }
        : e,
    );
    set({
      elements: [frame, ...updated],
      selectedIds: [frameId],
      past: [...s.past, s.elements],
      future: [],
    });
  },

  ungroupElements: () => {
    const s = get();
    const frames = s.elements.filter(
      (e) => e.type === "frame" && s.selectedIds.includes(e.id),
    );
    if (frames.length === 0) return;
    const frameIds = new Set(frames.map((f) => f.id));
    const children = s.elements.filter(
      (e) => e.parentId && frameIds.has(e.parentId),
    );
    const childIds = children.map((c) => c.id);
    const updated = s.elements
      .filter((e) => !frameIds.has(e.id))
      .map((e) => {
        if (e.parentId && frameIds.has(e.parentId)) {
          const parent = frames.find((f) => f.id === e.parentId)!;
          return { ...e, parentId: null, x: e.x + parent.x, y: e.y + parent.y };
        }
        return e;
      });
    set({
      elements: updated,
      selectedIds: childIds,
      past: [...s.past, s.elements],
      future: [],
    });
  },

  // ------ Alignment ------
  alignElements: (alignment) => {
    const s = get();
    const selected = s.elements.filter((e) => s.selectedIds.includes(e.id));
    if (selected.length < 2) return;
    const bounds = {
      minX: Math.min(...selected.map((e) => e.x)),
      maxX: Math.max(...selected.map((e) => e.x + e.width)),
      minY: Math.min(...selected.map((e) => e.y)),
      maxY: Math.max(...selected.map((e) => e.y + e.height)),
    };
    const centerX = (bounds.minX + bounds.maxX) / 2;
    const centerY = (bounds.minY + bounds.maxY) / 2;
    const updates = selected.map((e) => {
      let changes: Partial<WorkspaceElement> = {};
      switch (alignment) {
        case "left": changes = { x: bounds.minX }; break;
        case "right": changes = { x: bounds.maxX - e.width }; break;
        case "top": changes = { y: bounds.minY }; break;
        case "bottom": changes = { y: bounds.maxY - e.height }; break;
        case "centerH": changes = { x: centerX - e.width / 2 }; break;
        case "centerV": changes = { y: centerY - e.height / 2 }; break;
      }
      return { id: e.id, changes };
    });
    s.pushHistory();
    s.updateElements(updates);
  },

  distributeElements: (direction) => {
    const s = get();
    const selected = s.elements.filter((e) => s.selectedIds.includes(e.id));
    if (selected.length < 3) return;
    s.pushHistory();
    if (direction === "horizontal") {
      const sorted = [...selected].sort((a, b) => a.x - b.x);
      const totalW = sorted.reduce((sum, e) => sum + e.width, 0);
      const minX = sorted[0].x;
      const maxEnd = sorted[sorted.length - 1].x + sorted[sorted.length - 1].width;
      const gap = (maxEnd - minX - totalW) / (sorted.length - 1);
      let currentX = minX;
      const updates = sorted.map((e) => {
        const changes = { x: currentX };
        currentX += e.width + gap;
        return { id: e.id, changes };
      });
      s.updateElements(updates);
    } else {
      const sorted = [...selected].sort((a, b) => a.y - b.y);
      const totalH = sorted.reduce((sum, e) => sum + e.height, 0);
      const minY = sorted[0].y;
      const maxEnd = sorted[sorted.length - 1].y + sorted[sorted.length - 1].height;
      const gap = (maxEnd - minY - totalH) / (sorted.length - 1);
      let currentY = minY;
      const updates = sorted.map((e) => {
        const changes = { y: currentY };
        currentY += e.height + gap;
        return { id: e.id, changes };
      });
      s.updateElements(updates);
    }
  },

  // ------ History ------
  pushHistory: () =>
    set((s) => ({
      past: [...s.past.slice(-50), s.elements],
      future: [],
    })),

  undo: () => {
    const s = get();
    if (s.past.length === 0) return;
    const previous = s.past[s.past.length - 1];
    set({
      elements: previous,
      past: s.past.slice(0, -1),
      future: [s.elements, ...s.future],
      selectedIds: [],
    });
  },

  redo: () => {
    const s = get();
    if (s.future.length === 0) return;
    const next = s.future[0];
    set({
      elements: next,
      past: [...s.past, s.elements],
      future: s.future.slice(1),
      selectedIds: [],
    });
  },

  // ------ Toggles ------
  toggleGrid: () => set((s) => ({ showGrid: !s.showGrid })),
  toggleSnap: () => set((s) => ({ snapEnabled: !s.snapEnabled })),

  toggleLock: (id) =>
    set((s) => ({
      elements: s.elements.map((e) =>
        e.id === id ? { ...e, locked: !e.locked } : e,
      ),
    })),

  toggleVisibility: (id) =>
    set((s) => ({
      elements: s.elements.map((e) =>
        e.id === id ? { ...e, visible: !e.visible } : e,
      ),
    })),

  // ------ Clipboard ------
  copyElements: () => {
    const s = get();
    set({
      clipboard: s.elements.filter((e) => s.selectedIds.includes(e.id)),
    });
  },

  cutElements: () => {
    const s = get();
    const toCut = s.elements.filter((e) => s.selectedIds.includes(e.id));
    set({
      clipboard: toCut,
      elements: s.elements.filter((e) => !s.selectedIds.includes(e.id)),
      selectedIds: [],
      past: [...s.past, s.elements],
      future: [],
    });
  },

  pasteElements: () => {
    const s = get();
    if (s.clipboard.length === 0) return;
    const newEls = s.clipboard.map((e) => ({
      ...e,
      id: nanoid(10),
      name: `${e.name} copy`,
      x: e.x + 20,
      y: e.y + 20,
    }));
    set({
      elements: [...s.elements, ...newEls],
      selectedIds: newEls.map((e) => e.id),
      past: [...s.past, s.elements],
      future: [],
    });
  },

  renameElement: (id, name) =>
    set((s) => ({
      elements: s.elements.map((e) =>
        e.id === id ? { ...e, name } : e,
      ),
    })),

  loadElements: (elements) => {
    const s = get();
    set({
      elements,
      selectedIds: [],
      past: [...s.past, s.elements],
      future: [],
    });
  },

  clearAll: () => {
    const s = get();
    set({
      elements: [],
      selectedIds: [],
      past: [...s.past, s.elements],
      future: [],
    });
  },

  resetToTemplate: () => {
    const s = get();
    set({
      elements: INITIAL_ELEMENTS,
      selectedIds: [],
      canvas: { panX: 40, panY: 40, zoom: 0.85 },
      past: [...s.past, s.elements],
      future: [],
    });
  },
}));
