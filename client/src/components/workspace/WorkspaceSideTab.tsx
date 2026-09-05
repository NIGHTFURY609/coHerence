import { useState, useRef } from "react";
import { ChevronDown, FolderPlus, Check, Globe, ExternalLink, Image as ImageIcon, Plus } from "lucide-react";
import { toast } from "sonner";
import { useWorkspaceStore } from "@/stores/workspaceStore";
import AddWebsiteModal from "./AddWebsiteModal";

export default function WorkspaceSideTab() {
  const [openProgress, setOpenProgress] = useState(true);
  const [openOutputs, setOpenOutputs] = useState(true);
  const [openContext, setOpenContext] = useState(true);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [isWebsiteModalOpen, setIsWebsiteModalOpen] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);
  const { elements, addElement, selectElement, canvas } = useWorkspaceStore();

  const referencedWebsites = elements.filter((e) => e.type === "website" && e.url);
  const referencedImages = elements.filter((e) => e.type === "image");

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
            addElement({
              type: "image",
              name: file.name.replace(/\.[^/.]+$/, ""),
              x: 100 + i * 30,
              y: 100 + i * 30,
              width: 300,
              height: 200,
              src: dataUrl,
            });
          };
          reader.readAsDataURL(file);
        }
      });
      toast.success(`Imported ${files.length} media file${files.length > 1 ? "s" : ""}`);
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
            <ChevronDown
              size={15}
              strokeWidth={2}
              className={`ws-sidetab-chevron ${openProgress ? "is-open" : "is-collapsed"}`}
            />
          </div>
        </button>

        {openProgress && (
          <div className="ws-sidetab-content">
            {/* Stepper Graphic */}
            <div className="ws-sidetab-stepper" role="progressbar" aria-label="Task progress">
              <div className="ws-sidetab-step-circle completed">
                <Check size={14} strokeWidth={2.2} />
              </div>
              <div className="ws-sidetab-step-line" />
              <div className="ws-sidetab-step-circle completed">
                <Check size={14} strokeWidth={2.2} />
              </div>
              <div className="ws-sidetab-step-line" />
              <div className="ws-sidetab-step-circle pending" />
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
            <ChevronDown
              size={15}
              strokeWidth={2}
              className={`ws-sidetab-chevron ${openOutputs ? "is-open" : "is-collapsed"}`}
            />
          </div>
        </button>

        {openOutputs && (
          <div className="ws-sidetab-content">
            {/* Histogram / Bar Chart Card */}
            <div className="ws-sidetab-output-card" title="Outputs visualizer">
              <svg
                width="38"
                height="26"
                viewBox="0 0 38 26"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="ws-sidetab-chart-svg"
              >
                {/* Baseline */}
                <rect x="3" y="22" width="32" height="2.5" rx="1.25" fill="rgba(255, 255, 255, 0.28)" />
                {/* Bar 1 */}
                <rect x="7" y="14" width="5.5" height="7.5" rx="1.5" fill="rgba(255, 255, 255, 0.28)" />
                {/* Bar 2 */}
                <rect x="16" y="8" width="5.5" height="13.5" rx="1.5" fill="rgba(255, 255, 255, 0.28)" />
                {/* Bar 3 */}
                <rect x="25" y="3" width="5.5" height="18.5" rx="1.5" fill="rgba(255, 255, 255, 0.28)" />
              </svg>
            </div>

            <p className="ws-sidetab-desc">View and open files created during this task.</p>
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
              <ChevronDown
                size={15}
                strokeWidth={2}
                className={`ws-sidetab-chevron ${openContext ? "is-open" : "is-collapsed"}`}
              />
            </div>
          </button>

          <button
            type="button"
            className="ws-sidetab-add-btn"
            onClick={handleAddContextClick}
            title="Add referenced website or media file"
            aria-label="Add context"
          >
            <FolderPlus size={16} strokeWidth={1.8} />
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
                <Globe size={14} style={{ color: "#d85c45" }} />
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
                <ImageIcon size={14} style={{ color: "#77a88d" }} />
                <span>Upload Media Image</span>
              </button>
            </div>
          )}
        </div>

        {openContext && (
          <div className="ws-sidetab-content">
            {/* Context Cards Illustration from side tab.png */}
            <div className="ws-sidetab-context-illustration">
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
                    fill="#222222"
                    stroke="rgba(255, 255, 255, 0.2)"
                    strokeWidth="1.2"
                  />
                  {/* Wavy lines */}
                  <path
                    d="M 8 28 Q 11 26.5 14 28 T 20 28 T 26 28 T 32 28"
                    stroke="rgba(255, 255, 255, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 8 34 Q 11 32.5 14 34 T 20 34 T 26 34 T 32 34"
                    stroke="rgba(255, 255, 255, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 8 40 Q 11 38.5 14 40 T 20 40 T 26 40 T 32 40"
                    stroke="rgba(255, 255, 255, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 8 46 Q 11 44.5 14 46 T 20 46 T 26 46"
                    stroke="rgba(255, 255, 255, 0.25)"
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
                    fill="#222222"
                    stroke="rgba(255, 255, 255, 0.2)"
                    strokeWidth="1.2"
                  />
                  {/* Wavy lines */}
                  <path
                    d="M 50 28 Q 53 26.5 56 28 T 62 28 T 68 28 T 74 28"
                    stroke="rgba(255, 255, 255, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 50 34 Q 53 32.5 56 34 T 62 34 T 68 34 T 74 34"
                    stroke="rgba(255, 255, 255, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 50 40 Q 53 38.5 56 40 T 62 40 T 68 40 T 74 40"
                    stroke="rgba(255, 255, 255, 0.25)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 50 46 Q 53 44.5 56 46 T 62 46 T 68 46"
                    stroke="rgba(255, 255, 255, 0.25)"
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
                  stroke="rgba(255, 255, 255, 0.18)"
                  strokeWidth="1.2"
                  strokeDasharray="2.5 2.5"
                />

                {/* Card 3 (Elevated card in front with + badge) */}
                <g filter="url(#cardShadow)">
                  <rect
                    x="70"
                    y="4"
                    width="42"
                    height="50"
                    rx="8"
                    fill="#282828"
                    stroke="rgba(255, 255, 255, 0.3)"
                    strokeWidth="1.2"
                  />
                  {/* Wavy text lines on elevated card */}
                  <path
                    d="M 76 14 Q 79 12.5 82 14 T 88 14 T 94 14 T 100 14"
                    stroke="rgba(255, 255, 255, 0.3)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 76 20 Q 79 18.5 82 20 T 88 20 T 94 20 T 100 20"
                    stroke="rgba(255, 255, 255, 0.3)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <path
                    d="M 76 26 Q 79 24.5 82 26 T 88 26 T 94 26"
                    stroke="rgba(255, 255, 255, 0.3)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />

                  {/* Plus badge circle */}
                  <circle
                    cx="82"
                    cy="40"
                    r="6.5"
                    fill="#282828"
                    stroke="rgba(255, 255, 255, 0.32)"
                    strokeWidth="1.1"
                  />
                  {/* Plus horizontal and vertical strokes */}
                  <line
                    x1="78.5"
                    y1="40"
                    x2="85.5"
                    y2="40"
                    stroke="rgba(255, 255, 255, 0.45)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                  <line
                    x1="82"
                    y1="36.5"
                    x2="82"
                    y2="43.5"
                    stroke="rgba(255, 255, 255, 0.45)"
                    strokeWidth="1.2"
                    strokeLinecap="round"
                  />
                </g>

                <defs>
                  <filter id="cardShadow" x="66" y="2" width="50" height="58" filterUnits="userSpaceOnUse">
                    <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="#000000" floodOpacity="0.4" />
                  </filter>
                </defs>
              </svg>
            </div>

            {/* List active referenced websites/tools if any exist on canvas */}
            {(referencedWebsites.length > 0 || referencedImages.length > 0) && (
              <div className="ws-sidetab-refs">
                {referencedWebsites.map((site) => (
                  <div key={site.id} className="ws-sidetab-ref-item">
                    <button
                      type="button"
                      className="ws-sidetab-ref-link"
                      onClick={() => selectElement(site.id)}
                      title={`Select ${site.name} on canvas`}
                    >
                      <Globe size={13} className="ws-sidetab-ref-icon" />
                      <span>{site.name}</span>
                    </button>
                    {site.url && (
                      <a
                        href={site.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="ws-website-action-btn"
                        title="Open website in new window"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <ExternalLink size={12} />
                      </a>
                    )}
                  </div>
                ))}
                {referencedImages.map((img) => (
                  <div key={img.id} className="ws-sidetab-ref-item">
                    <button
                      type="button"
                      className="ws-sidetab-ref-link"
                      onClick={() => selectElement(img.id)}
                      title={`Select ${img.name} on canvas`}
                    >
                      <ImageIcon size={13} style={{ color: "#77a88d" }} />
                      <span>{img.name}</span>
                    </button>
                  </div>
                ))}
              </div>
            )}

            <p className="ws-sidetab-desc">Track tools and referenced files used in this task.</p>
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
