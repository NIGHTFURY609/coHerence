import { useRef, useState, useCallback, useEffect } from "react";
import { useWorkspaceStore, type ToolType } from "@/stores/workspaceStore";
import { toast } from "sonner";
import {
  MousePointer2,
  Hand,
  SquareDashed,
  Square,
  Circle,
  Minus,
  MoveRight,
  Type,
  ImagePlus,
  Undo2,
  Redo2,
  Grid3x3,
  Download,
  Upload,
  ZoomIn,
  ZoomOut,
  Sparkles,
  ChevronDown,
  RotateCcw,
  Trash2,
  FileCode,
  Globe,
} from "lucide-react";
import AddWebsiteModal from "./AddWebsiteModal";
import RunAuditModal from "./RunAuditModal";
import { cancelAudit, useAuditStore } from "@/stores/auditStore";

const tools: { tool: ToolType; icon: typeof Square; label: string; group: number }[] = [
  { tool: "select", icon: MousePointer2, label: "Select (V)", group: 0 },
  { tool: "hand", icon: Hand, label: "Hand (H)", group: 0 },
  { tool: "frame", icon: SquareDashed, label: "Frame (F)", group: 1 },
  { tool: "rectangle", icon: Square, label: "Rectangle (R)", group: 1 },
  { tool: "ellipse", icon: Circle, label: "Ellipse (O)", group: 1 },
  { tool: "line", icon: Minus, label: "Line (L)", group: 1 },
  { tool: "arrow", icon: MoveRight, label: "Arrow", group: 1 },
  { tool: "text", icon: Type, label: "Text (T)", group: 2 },
  { tool: "image", icon: ImagePlus, label: "Image (Media)", group: 2 },
  { tool: "website", icon: Globe, label: "Website / URL (W)", group: 2 },
];

export default function WorkspaceToolbar() {
  const {
    elements,
    selectedIds,
    activeTool,
    setActiveTool,
    addElement,
    loadElements,
    clearAll,
    resetToTemplate,
    undo,
    redo,
    past,
    future,
    canvas,
    zoomIn,
    zoomOut,
    showGrid,
    toggleGrid,
  } = useWorkspaceStore();

  const [exportOpen, setExportOpen] = useState(false);
  const [isWebsiteModalOpen, setIsWebsiteModalOpen] = useState(false);
  const [isAuditOpen, setIsAuditOpen] = useState(false);
  const auditRunning = useAuditStore((s) => s.running);
  const auditStage = useAuditStore((s) => s.stage);
  const imageInputRef = useRef<HTMLInputElement>(null);
  const jsonInputRef = useRef<HTMLInputElement>(null);

  const groups = [0, 1, 2];
  const zoomPct = Math.round(canvas.zoom * 100);

  useEffect(() => {
    const openWebsite = () => setIsWebsiteModalOpen(true);
    window.addEventListener("coherence-add-website", openWebsite);
    return () => window.removeEventListener("coherence-add-website", openWebsite);
  }, []);

  const handleToolClick = (tool: ToolType) => {
    if (tool === "image") {
      imageInputRef.current?.click();
      return;
    }
    if (tool === "website") {
      setIsWebsiteModalOpen(true);
      return;
    }
    setActiveTool(tool);
  };

  const handleAddWebsite = (
    url: string,
    name?: string,
    width: number = 680,
    height: number = 440,
  ) => {
    const ptX = -canvas.panX / canvas.zoom + 100;
    const ptY = -canvas.panY / canvas.zoom + 60;
    addElement({
      type: "website",
      name: name || "Website",
      url,
      x: Math.max(40, Math.round(ptX)),
      y: Math.max(40, Math.round(ptY)),
      width,
      height,
    });
    setActiveTool("select");
    toast.success(`Website embedded: ${name || url}`);
  };

  const handleImageFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const dataUrl = event.target?.result as string;
      addElement({
        type: "image",
        name: file.name.replace(/\.[^/.]+$/, ""),
        x: 140,
        y: 140,
        width: 320,
        height: 220,
        src: dataUrl,
      });
      setActiveTool("select");
      toast.success("Image placed on canvas");
    };
    reader.readAsDataURL(file);
    e.target.value = "";
  };

  const exportJSON = useCallback(() => {
    const data = JSON.stringify({ version: "1.0", elements }, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `coherence-workspace-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    setExportOpen(false);
    toast.success("Workspace exported as JSON");
  }, [elements]);

  const exportSVG = useCallback(() => {
    if (elements.length === 0) {
      toast.error("No elements to export");
      return;
    }
    const minX = Math.min(...elements.map((e) => e.x));
    const minY = Math.min(...elements.map((e) => e.y));
    const maxX = Math.max(...elements.map((e) => e.x + e.width));
    const maxY = Math.max(...elements.map((e) => e.y + e.height));
    const w = maxX - minX + 40;
    const h = maxY - minY + 40;

    let svgInner = "";
    for (const el of elements.filter((e) => e.visible)) {
      const relX = el.x - minX + 20;
      const relY = el.y - minY + 20;
      if (el.type === "rectangle" || el.type === "frame") {
        svgInner += `<rect x="${relX}" y="${relY}" width="${el.width}" height="${el.height}" rx="${el.cornerRadius || 0}" fill="${el.fill}" opacity="${el.fillOpacity}" stroke="${el.stroke || "none"}" stroke-width="${el.strokeWidth || 0}" />\n`;
      } else if (el.type === "ellipse") {
        svgInner += `<ellipse cx="${relX + el.width / 2}" cy="${relY + el.height / 2}" rx="${el.width / 2}" ry="${el.height / 2}" fill="${el.fill}" opacity="${el.fillOpacity}" stroke="${el.stroke || "none"}" stroke-width="${el.strokeWidth || 0}" />\n`;
      } else if (el.type === "text") {
        svgInner += `<text x="${relX}" y="${relY + (el.fontSize || 16)}" font-family="${el.fontFamily || "Manrope"}" font-size="${el.fontSize || 16}" font-weight="${el.fontWeight || 500}" fill="${el.textColor || "#173B36"}">${el.text || ""}</text>\n`;
      } else if (el.type === "line") {
        svgInner += `<line x1="${relX}" y1="${relY}" x2="${relX + (el.x2 ?? el.width)}" y2="${relY + (el.y2 ?? 0)}" stroke="${el.stroke || "#173B36"}" stroke-width="${el.strokeWidth || 2}" />\n`;
      } else if (el.type === "website") {
        svgInner += `<rect x="${relX}" y="${relY}" width="${el.width}" height="${el.height}" rx="${el.cornerRadius || 8}" fill="#1e1e1e" stroke="rgba(255,255,255,0.2)" stroke-width="1" />\n`;
        svgInner += `<text x="${relX + 16}" y="${relY + 24}" font-family="Manrope" font-size="12" font-weight="700" fill="#f0f0f0">${el.name || "Website"}</text>\n`;
        svgInner += `<text x="${relX + 16}" y="${relY + 44}" font-family="Manrope" font-size="10" fill="#888888">${el.url || ""}</text>\n`;
      }
    }

    const svg = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${w} ${h}" width="${w}" height="${h}">\n${svgInner}</svg>`;
    const blob = new Blob([svg], { type: "image/svg+xml" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `coherence-design-${Date.now()}.svg`;
    a.click();
    URL.revokeObjectURL(url);
    setExportOpen(false);
    toast.success("Design exported as SVG");
  }, [elements]);

  const handleImportJSON = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      try {
        const parsed = JSON.parse(event.target?.result as string);
        if (Array.isArray(parsed.elements)) {
          loadElements(parsed.elements);
          toast.success(`Imported ${parsed.elements.length} elements`);
        } else if (Array.isArray(parsed)) {
          loadElements(parsed);
          toast.success(`Imported ${parsed.length} elements`);
        }
      } catch (err) {
        toast.error("Invalid workspace JSON file");
      }
    };
    reader.readAsText(file);
    e.target.value = "";
  };

  const runFairnessAudit = useCallback(() => {
    const selected = elements.filter(
      (e) => e.type === "website" && e.url && selectedIds.includes(e.id),
    );
    const websites = selected.length
      ? selected
      : elements.filter((e) => e.type === "website" && e.url);
    if (websites.length === 0) {
      toast.info("Embed a website first, then run Audit");
      return;
    }
    setIsAuditOpen(true);
  }, [elements, selectedIds]);

  return (
    <header className="ws-toolbar">
      <input
        ref={imageInputRef}
        type="file"
        accept="image/*"
        style={{ display: "none" }}
        onChange={handleImageFile}
      />
      <input
        ref={jsonInputRef}
        type="file"
        accept=".json"
        style={{ display: "none" }}
        onChange={handleImportJSON}
      />

      <a className="ws-toolbar-brand" href="/" aria-label="Return home">
        <span className="mark">C</span>
        <span>
          Co<span style={{ color: "#D85C45" }}>HER</span>ence
          <small>/ workspace</small>
        </span>
      </a>

      <div className="ws-toolbar-center">
        {groups.map((g) => (
          <div className="ws-toolbar-group" key={g}>
            {tools
              .filter((t) => t.group === g)
              .map((t) => (
                <button
                  key={t.tool}
                  type="button"
                  className={`ws-toolbar-button${activeTool === t.tool ? " ws-toolbar-button--active" : ""}`}
                  title={t.label}
                  onClick={() => handleToolClick(t.tool)}
                >
                  <t.icon size={16} />
                </button>
              ))}
          </div>
        ))}
      </div>

      <div className="ws-toolbar-actions">
        {/* Fairness audit simulation trigger */}
        <button
          type="button"
          className="ws-toolbar-audit-btn"
          title={
            auditRunning
              ? `Capturing${auditStage ? ` · ${auditStage}` : ""} — click to cancel or restart`
              : "Run Accessibility & Fairness Audit"
          }
          onClick={runFairnessAudit}
        >
          <Sparkles size={13} style={{ color: "#D85C45" }} />
          <span>{auditRunning ? "Capturing…" : "Audit"}</span>
        </button>

        <div className="ws-toolbar-divider" />

        <button
          type="button"
          className="ws-toolbar-button"
          title="Undo (Ctrl+Z)"
          disabled={past.length === 0}
          onClick={undo}
        >
          <Undo2 size={16} />
        </button>
        <button
          type="button"
          className="ws-toolbar-button"
          title="Redo (Ctrl+Shift+Z)"
          disabled={future.length === 0}
          onClick={redo}
        >
          <Redo2 size={16} />
        </button>

        <div className="ws-toolbar-divider" />

        <div className="ws-toolbar-zoom">
          <button
            type="button"
            className="ws-toolbar-button"
            title="Zoom Out"
            onClick={zoomOut}
          >
            <ZoomOut size={14} />
          </button>
          <span>{zoomPct}%</span>
          <button
            type="button"
            className="ws-toolbar-button"
            title="Zoom In"
            onClick={zoomIn}
          >
            <ZoomIn size={14} />
          </button>
        </div>

        <div className="ws-toolbar-divider" />

        <button
          type="button"
          className={`ws-toolbar-button${showGrid ? " ws-toolbar-button--active" : ""}`}
          title="Toggle Grid"
          onClick={toggleGrid}
        >
          <Grid3x3 size={16} />
        </button>

        {/* Export / File menu */}
        <div style={{ position: "relative" }}>
          <button
            type="button"
            className="ws-toolbar-button"
            title="Export / File Options"
            onClick={() => setExportOpen((prev) => !prev)}
            style={{ display: "flex", gap: 2 }}
          >
            <Download size={15} />
            <ChevronDown size={11} style={{ opacity: 0.6 }} />
          </button>

          {exportOpen && (
            <div
              className="ws-context-menu"
              style={{
                position: "absolute",
                top: "100%",
                right: 0,
                marginTop: 4,
                zIndex: 200,
              }}
            >
              <button
                type="button"
                className="ws-context-menu-item"
                onClick={exportSVG}
              >
                <FileCode size={14} /> Export SVG
              </button>
              <button
                type="button"
                className="ws-context-menu-item"
                onClick={exportJSON}
              >
                <Download size={14} /> Save Workspace (.json)
              </button>
              <button
                type="button"
                className="ws-context-menu-item"
                onClick={() => {
                  setExportOpen(false);
                  jsonInputRef.current?.click();
                }}
              >
                <Upload size={14} /> Load Workspace (.json)
              </button>
              <div className="ws-context-menu-separator" />
              <button
                type="button"
                className="ws-context-menu-item"
                onClick={() => {
                  setExportOpen(false);
                  resetToTemplate();
                  toast.success("Workspace reset to template");
                }}
              >
                <RotateCcw size={14} /> Reset to Starter Template
              </button>
              <button
                type="button"
                className="ws-context-menu-item"
                style={{ color: "#D85C45" }}
                onClick={() => {
                  setExportOpen(false);
                  clearAll();
                  toast.info("Canvas cleared");
                }}
              >
                <Trash2 size={14} /> Clear Canvas
              </button>
            </div>
          )}
        </div>
      </div>
      <AddWebsiteModal
        isOpen={isWebsiteModalOpen}
        onClose={() => setIsWebsiteModalOpen(false)}
        onAdd={handleAddWebsite}
      />
      <RunAuditModal
        isOpen={isAuditOpen}
        onClose={() => setIsAuditOpen(false)}
        url={
          (
            elements.find(
              (e) => e.type === "website" && e.url && selectedIds.includes(e.id),
            ) ?? elements.find((e) => e.type === "website" && e.url)
          )?.url || ""
        }
      />
    </header>
  );
}
