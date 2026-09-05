import { useState, useRef, useCallback } from "react";
import {
  ChevronDown,
  FolderPlus,
  Check,
  Globe,
  ExternalLink,
  Image as ImageIcon,
  Plus,
  Download,
  FileCode,
  Trash2,
  StickyNote,
  Compass,
} from "lucide-react";
import { toast } from "sonner";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import AddWebsiteModal from "./AddWebsiteModal";

interface MilestoneStep {
  id: string;
  label: string;
  completed: boolean;
}

export default function WorkspaceSideTab() {
  const [openProgress, setOpenProgress] = useState(true);
  const [openOutputs, setOpenOutputs] = useState(true);
  const [openContext, setOpenContext] = useState(true);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [isWebsiteModalOpen, setIsWebsiteModalOpen] = useState(false);

  // Functional milestones in progress
  const [steps, setSteps] = useState<MilestoneStep[]>([
    { id: "1", label: "Research & References", completed: true },
    { id: "2", label: "Composition & Layout", completed: true },
    { id: "3", label: "Review & Finalize", completed: false },
  ]);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const {
    elements,
    addElement,
    selectElement,
    deleteElements,
    setCanvasTransform,
    canvas,
  } = useWorkspaceStore();

  const referencedWebsites = elements.filter((e) => e.type === "website" && e.url);
  const referencedImages = elements.filter((e) => e.type === "image");

  const completedStepsCount = steps.filter((s) => s.completed).length;
  const progressPct = Math.round((completedStepsCount / steps.length) * 100);

  const toggleStep = (id: string) => {
    setSteps((prev) =>
      prev.map((s) => {
        if (s.id === id) {
          const next = !s.completed;
          toast.success(
            next
              ? `Completed milestone: ${s.label}`
              : `Marked milestone pending: ${s.label}`,
          );
          return { ...s, completed: next };
        }
        return s;
      }),
    );
  };

  const handleAddContextClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowAddMenu((prev) => !prev);
  };

  const handleFileSelected = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      Array.from(files).forEach((file, i) => {
        if (file.type.startsWith("image/")) {
          const reader = new FileReader();
          reader.onload = (event) => {
            const dataUrl = event.target?.result as string;
            const id = addElement({
              type: "image",
              name: file.name.replace(/\.[^/.]+$/, ""),
              x: 100 + i * 30,
              y: 100 + i * 30,
              width: 300,
              height: 200,
              src: dataUrl,
            });
            selectElement(id);
          };
          reader.readAsDataURL(file);
        }
      });
      toast.success(
        `Imported ${files.length} media file${files.length > 1 ? "s" : ""}`,
      );
      e.target.value = "";
    }
  };

  const handleAddWebsite = (
    url: string,
    name?: string,
    width: number = 680,
    height: number = 440,
  ) => {
    const ptX = -canvas.panX / canvas.zoom + 100;
    const ptY = -canvas.panY / canvas.zoom + 60;
    const id = addElement({
      type: "website",
      name: name || "Website",
      url,
      x: Math.max(40, Math.round(ptX)),
      y: Math.max(40, Math.round(ptY)),
      width,
      height,
    });
    selectElement(id);
    toast.success(`Website embedded: ${name || url}`);
  };

  const handleAddNote = () => {
    const ptX = -canvas.panX / canvas.zoom + 120;
    const ptY = -canvas.panY / canvas.zoom + 80;
    const id = addElement({
      type: "text",
      name: "Reference Note",
      text: "Notes & References:\n• Key specs and layout details\n• Verified civic resources",
      x: Math.max(40, Math.round(ptX)),
      y: Math.max(40, Math.round(ptY)),
      width: 260,
      height: 100,
      fontSize: 14,
      textColor: "#F7F1E7",
      fill: "#1A3631",
      fillOpacity: 0.9,
      stroke: "#D85C45",
      strokeWidth: 1,
      cornerRadius: 6,
    });
    selectElement(id);
    toast.success("Reference note added to canvas");
  };

  const handleFocusReference = (id: string, name: string) => {
    selectElement(id);
    const el = elements.find((e) => e.id === id);
    if (el) {
      const viewportWidth = window.innerWidth - 320;
      const viewportHeight = window.innerHeight - 90;
      const targetPanX = viewportWidth / 2 - (el.x + el.width / 2) * canvas.zoom;
      const targetPanY = viewportHeight / 2 - (el.y + el.height / 2) * canvas.zoom;
      setCanvasTransform({
        panX: Math.round(targetPanX),
        panY: Math.round(targetPanY),
      });
      toast.info(`Focused on ${name}`);
    }
  };

  const exportJSON = useCallback(() => {
    if (elements.length === 0) {
      toast.info("Canvas is empty");
      return;
    }
    const data = JSON.stringify(elements, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `coherence-workspace-${Date.now()}.json`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Workspace saved as JSON");
  }, [elements]);

  const exportSVG = useCallback(() => {
    if (elements.length === 0) {
      toast.error("No elements on canvas to export");
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
        svgInner += `<text x="${relX}" y="${relY + (el.fontSize || 16)}" font-family="${el.fontFamily || "Manrope"}" font-size="${el.fontSize || 16}" font-weight="${el.fontWeight || 500}" fill="${el.textColor || "#F7F1E7"}">${el.text || ""}</text>\n`;
      } else if (el.type === "line") {
        svgInner += `<line x1="${relX}" y1="${relY}" x2="${relX + (el.x2 ?? el.width)}" y2="${relY + (el.y2 ?? 0)}" stroke="${el.stroke || "#173B36"}" stroke-width="${el.strokeWidth || 2}" />\n`;
      } else if (el.type === "website") {
        svgInner += `<rect x="${relX}" y="${relY}" width="${el.width}" height="${el.height}" rx="${el.cornerRadius || 8}" fill="#142925" stroke="rgba(247,241,231,0.2)" stroke-width="1" />\n`;
        svgInner += `<text x="${relX + 16}" y="${relY + 24}" font-family="Manrope" font-size="12" font-weight="700" fill="#f7f1e7">${el.name || "Website"}</text>\n`;
        svgInner += `<text x="${relX + 16}" y="${relY + 44}" font-family="Manrope" font-size="10" fill="#c9d9b2">${el.url || ""}</text>\n`;
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
    toast.success("Design exported as SVG");
  }, [elements]);

  return (
    <aside className="ws-sidetab" aria-label="Task Side Tab">
      <input
        ref={fileInputRef}
        type="file"
        accept="image/*"
        multiple
        style={{ display: "none" }}
        onChange={handleFileSelected}
      />

      {/* 1. Progress Section */}
      <div className="ws-sidetab-section">
        <button
          type="button"
          className="ws-sidetab-header"
          onClick={() => setOpenProgress(!openProgress)}
          aria-expanded={openProgress}
        >
          <div className="ws-sidetab-title-wrap">
            <span className="ws-sidetab-title">Progress</span>
            <span className="ws-sidetab-badge">
              {completedStepsCount}/{steps.length}
            </span>
            <ChevronDown
              size={14}
              strokeWidth={2}
              className={`ws-sidetab-chevron ${openProgress ? "is-open" : "is-collapsed"}`}
            />
          </div>
        </button>

        {openProgress && (
          <div className="ws-sidetab-content">
            {/* Functional Stepper Graphic */}
            <div
              className="ws-sidetab-stepper"
              role="progressbar"
              aria-label="Task progress"
              title="Click any step to toggle completion"
            >
              {steps.map((step, idx) => (
                <div key={step.id} style={{ display: "flex", alignItems: "center" }}>
                  <button
                    type="button"
                    className="ws-sidetab-step-btn"
                    onClick={() => toggleStep(step.id)}
                    title={`Step ${idx + 1}: ${step.label} (${step.completed ? "Complete" : "Pending"})`}
                  >
                    <div
                      className={`ws-sidetab-step-circle ${step.completed ? "completed" : idx === 2 ? "active" : ""}`}
                    >
                      {step.completed && <Check size={13} strokeWidth={2.4} />}
                    </div>
                  </button>
                  {idx < steps.length - 1 && (
                    <div
                      className={`ws-sidetab-step-line ${step.completed ? "completed" : ""}`}
                    />
                  )}
                </div>
              ))}
            </div>

            {/* Stepper info card */}
            <div className="ws-sidetab-step-info">
              <span className="ws-sidetab-step-label">
                {completedStepsCount === steps.length
                  ? "All milestones completed"
                  : `Milestone ${completedStepsCount + 1}: ${steps.find((s) => !s.completed)?.label || "Done"}`}
              </span>
              <span className="ws-sidetab-step-pct">{progressPct}%</span>
            </div>

            <p className="ws-sidetab-desc">See task progress for longer tasks.</p>
          </div>
        )}
      </div>

      {/* 2. Outputs Section */}
      <div className="ws-sidetab-section">
        <button
          type="button"
          className="ws-sidetab-header"
          onClick={() => setOpenOutputs(!openOutputs)}
          aria-expanded={openOutputs}
        >
          <div className="ws-sidetab-title-wrap">
            <span className="ws-sidetab-title">Outputs</span>
            <span className="ws-sidetab-badge">{elements.length}</span>
            <ChevronDown
              size={14}
              strokeWidth={2}
              className={`ws-sidetab-chevron ${openOutputs ? "is-open" : "is-collapsed"}`}
            />
          </div>
        </button>

        {openOutputs && (
          <div className="ws-sidetab-content">
            {/* Histogram / Bar Chart Card with functional metrics */}
            <div className="ws-sidetab-output-row">
              <div
                className="ws-sidetab-output-card"
                title="Click to export design as SVG"
                onClick={exportSVG}
              >
                <svg
                  width="36"
                  height="26"
                  viewBox="0 0 38 26"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  {/* Baseline */}
                  <rect
                    x="3"
                    y="22"
                    width="32"
                    height="2.5"
                    rx="1.25"
                    fill="rgba(247, 241, 231, 0.35)"
                  />
                  {/* Bar 1 (Pistachio) */}
                  <rect
                    x="7"
                    y="14"
                    width="5.5"
                    height="7.5"
                    rx="1.5"
                    fill="#C9D9B2"
                  />
                  {/* Bar 2 (Clay) */}
                  <rect
                    x="16"
                    y="8"
                    width="5.5"
                    height="13.5"
                    rx="1.5"
                    fill="#D85C45"
                  />
                  {/* Bar 3 (Pistachio light) */}
                  <rect
                    x="25"
                    y="3"
                    width="5.5"
                    height="18.5"
                    rx="1.5"
                    fill="#77A88D"
                  />
                </svg>
              </div>

              <div className="ws-sidetab-output-meta">
                <span className="ws-sidetab-output-count">
                  {elements.length} Canvas Element{elements.length === 1 ? "" : "s"}
                </span>
                <span className="ws-sidetab-output-sub">
                  {referencedWebsites.length} site{referencedWebsites.length === 1 ? "" : "s"} • {referencedImages.length} media
                </span>
              </div>
            </div>

            {/* Functional Export Actions */}
            <div className="ws-sidetab-output-actions">
              <button
                type="button"
                className="ws-sidetab-action-pill"
                onClick={exportSVG}
                title="Download design as vector SVG"
              >
                <FileCode size={12} style={{ color: "#C9D9B2" }} />
                <span>Export SVG</span>
              </button>
              <button
                type="button"
                className="ws-sidetab-action-pill"
                onClick={exportJSON}
                title="Save workspace file (.json)"
              >
                <Download size={12} style={{ color: "#D85C45" }} />
                <span>Save JSON</span>
              </button>
            </div>

            <p className="ws-sidetab-desc">
              View and open files created during this task.
            </p>
          </div>
        )}
      </div>

      {/* 3. Context Section */}
      <div className="ws-sidetab-section" style={{ position: "relative" }}>
        <div className="ws-sidetab-header-row">
          <button
            type="button"
            className="ws-sidetab-header"
            onClick={() => setOpenContext(!openContext)}
            aria-expanded={openContext}
          >
            <div className="ws-sidetab-title-wrap">
              <span className="ws-sidetab-title">Context</span>
              <span className="ws-sidetab-badge">
                {referencedWebsites.length + referencedImages.length}
              </span>
              <ChevronDown
                size={14}
                strokeWidth={2}
                className={`ws-sidetab-chevron ${openContext ? "is-open" : "is-collapsed"}`}
              />
            </div>
          </button>

          <button
            type="button"
            className="ws-sidetab-add-btn"
            onClick={handleAddContextClick}
            title="Add referenced website, media, or note"
            aria-label="Add context"
          >
            <FolderPlus size={15} strokeWidth={1.8} />
          </button>

          {/* Quick context add dropdown menu */}
          {showAddMenu && (
            <div className="ws-sidetab-menu">
              <button
                type="button"
                className="ws-sidetab-menu-item"
                onClick={() => {
                  setShowAddMenu(false);
                  setIsWebsiteModalOpen(true);
                }}
              >
                <Globe size={13} style={{ color: "#D85C45" }} />
                <span>Add Website / URL</span>
              </button>
              <button
                type="button"
                className="ws-sidetab-menu-item"
                onClick={() => {
                  setShowAddMenu(false);
                  fileInputRef.current?.click();
                }}
              >
                <ImageIcon size={13} style={{ color: "#77A88D" }} />
                <span>Upload Media Image</span>
              </button>
              <button
                type="button"
                className="ws-sidetab-menu-item"
                onClick={() => {
                  setShowAddMenu(false);
                  handleAddNote();
                }}
              >
                <StickyNote size={13} style={{ color: "#C9D9B2" }} />
                <span>Add Reference Note</span>
              </button>
            </div>
          )}
        </div>

        {openContext && (
          <div className="ws-sidetab-content">
            {/* Context Cards Illustration from side tab.png - clicking opens Add menu */}
            <div
              className="ws-sidetab-context-illustration"
              title="Click to add referenced context or resource"
              onClick={() => setShowAddMenu(true)}
            >
              <svg
                width="142"
                height="68"
                viewBox="0 0 142 68"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
              >
                {/* Card 1 (Left) */}
                <g>
                  <rect
                    x="2"
                    y="18"
                    width="36"
                    height="44"
                    rx="6"
                    fill="#152B27"
                    stroke="rgba(247, 241, 231, 0.16)"
                    strokeWidth="1.2"
                  />
                  <path
                    d="M 8 28 Q 11 26.5 14 28 T 20 28 T 26 28 T 32 28"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 8 34 Q 11 32.5 14 34 T 20 34 T 26 34 T 32 34"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 8 40 Q 11 38.5 14 40 T 20 40 T 26 40 T 32 40"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 8 46 Q 11 44.5 14 46 T 20 46 T 26 46"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                </g>

                {/* Card 2 (Middle) */}
                <g>
                  <rect
                    x="44"
                    y="18"
                    width="36"
                    height="44"
                    rx="6"
                    fill="#152B27"
                    stroke="rgba(247, 241, 231, 0.16)"
                    strokeWidth="1.2"
                  />
                  <path
                    d="M 50 28 Q 53 26.5 56 28 T 62 28 T 68 28 T 74 28"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 50 34 Q 53 32.5 56 34 T 62 34 T 68 34 T 74 34"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 50 40 Q 53 38.5 56 40 T 62 40 T 68 40 T 74 40"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 50 46 Q 53 44.5 56 46 T 62 46 T 68 46"
                    stroke="rgba(247, 241, 231, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                </g>

                {/* Card 4 (Right dashed outline) */}
                <rect
                  x="86"
                  y="18"
                  width="36"
                  height="44"
                  rx="6"
                  fill="none"
                  stroke="rgba(247, 241, 231, 0.16)"
                  strokeWidth="1.2"
                  strokeDasharray="2.5 2.5"
                />

                {/* Card 3 (Elevated card in front with + badge) */}
                <g filter="url(#civicCardShadow)">
                  <rect
                    x="70"
                    y="4"
                    width="42"
                    height="50"
                    rx="8"
                    fill="#1A3B35"
                    stroke="#D85C45"
                    strokeWidth="1.3"
                  />
                  <path
                    d="M 76 14 Q 79 12.5 82 14 T 88 14 T 94 14 T 100 14"
                    stroke="rgba(247, 241, 231, 0.35)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 76 20 Q 79 18.5 82 20 T 88 20 T 94 20 T 100 20"
                    stroke="rgba(247, 241, 231, 0.35)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 76 26 Q 79 24.5 82 26 T 88 26 T 94 26"
                    stroke="rgba(247, 241, 231, 0.35)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />

                  {/* Plus badge circle */}
                  <circle
                    cx="82"
                    cy="40"
                    r="7"
                    fill="#D85C45"
                    stroke="#F7F1E7"
                    strokeWidth="0.8"
                  />
                  <line
                    x1="78.5"
                    y1="40"
                    x2="85.5"
                    y2="40"
                    stroke="#FFFFFF"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                  <line
                    x1="82"
                    y1="36.5"
                    x2="82"
                    y2="43.5"
                    stroke="#FFFFFF"
                    strokeWidth="1.4"
                    strokeLinecap="round"
                  />
                </g>

                <defs>
                  <filter
                    id="civicCardShadow"
                    x="64"
                    y="2"
                    width="54"
                    height="60"
                    filterUnits="userSpaceOnUse"
                  >
                    <feDropShadow
                      dx="0"
                      dy="4"
                      stdDeviation="3.5"
                      floodColor="#000000"
                      floodOpacity="0.55"
                    />
                  </filter>
                </defs>
              </svg>
            </div>

            {/* List active referenced websites/tools if any exist on canvas */}
            {referencedWebsites.length > 0 || referencedImages.length > 0 ? (
              <div className="ws-sidetab-refs">
                {referencedWebsites.map((site) => (
                  <div key={site.id} className="ws-sidetab-ref-item">
                    <button
                      type="button"
                      className="ws-sidetab-ref-link"
                      onClick={() => handleFocusReference(site.id, site.name)}
                      title={`Click to focus and select ${site.name} on canvas`}
                    >
                      <Globe
                        size={13}
                        style={{ color: "#D85C45", flexShrink: 0 }}
                      />
                      <span>{site.name}</span>
                    </button>
                    <div className="ws-sidetab-ref-actions">
                      {site.url && (
                        <a
                          href={site.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="ws-sidetab-ref-icon-btn"
                          title="Open website in new browser tab"
                          onClick={(e) => e.stopPropagation()}
                        >
                          <ExternalLink size={12} />
                        </a>
                      )}
                      <button
                        type="button"
                        className="ws-sidetab-ref-icon-btn danger"
                        title="Delete from canvas"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteElements([site.id]);
                          toast.info(`Removed ${site.name}`);
                        }}
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>
                ))}

                {referencedImages.map((img) => (
                  <div key={img.id} className="ws-sidetab-ref-item">
                    <button
                      type="button"
                      className="ws-sidetab-ref-link"
                      onClick={() => handleFocusReference(img.id, img.name)}
                      title={`Click to focus and select ${img.name} on canvas`}
                    >
                      <ImageIcon
                        size={13}
                        style={{ color: "#77A88D", flexShrink: 0 }}
                      />
                      <span>{img.name}</span>
                    </button>
                    <div className="ws-sidetab-ref-actions">
                      <button
                        type="button"
                        className="ws-sidetab-ref-icon-btn danger"
                        title="Delete from canvas"
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteElements([img.id]);
                          toast.info(`Removed ${img.name}`);
                        }}
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <button
                type="button"
                className="ws-sidetab-action-pill"
                style={{ alignSelf: "flex-start", marginTop: 2 }}
                onClick={() => setShowAddMenu(true)}
              >
                <Plus size={12} style={{ color: "#D85C45" }} />
                <span>Add Reference Resource</span>
              </button>
            )}

            <p className="ws-sidetab-desc">
              Track tools and referenced files used in this task.
            </p>
          </div>
        )}
      </div>

      {/* Website Modal triggered from Side Tab */}
      <AddWebsiteModal
        isOpen={isWebsiteModalOpen}
        onClose={() => setIsWebsiteModalOpen(false)}
        onAdd={handleAddWebsite}
      />
    </aside>
  );
}
