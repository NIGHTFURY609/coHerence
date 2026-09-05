import { useState, useEffect, useRef } from "react";
import { Globe, X, Laptop, Smartphone, Monitor, ExternalLink } from "lucide-react";

interface AddWebsiteModalProps {
  isOpen: boolean;
  onClose: () => void;
  onAdd: (url: string, name?: string, width?: number, height?: number) => void;
}

const PRESET_SITES = [
  { label: "Wikipedia", url: "https://en.wikipedia.org" },
  { label: "Netflix", url: "https://www.netflix.com/browse" },
  { label: "YouTube", url: "https://www.youtube.com" },
  { label: "MDN Docs", url: "https://developer.mozilla.org" },
  { label: "GitHub", url: "https://github.com" },
  { label: "CoHERence Home", url: window.location.origin },
];

const PRESET_SIZES = [
  { label: "Desktop", width: 840, height: 540, icon: Monitor },
  { label: "Laptop", width: 680, height: 440, icon: Laptop },
  { label: "Mobile", width: 375, height: 667, icon: Smartphone },
];

export default function AddWebsiteModal({
  isOpen,
  onClose,
  onAdd,
}: AddWebsiteModalProps) {
  const [url, setUrl] = useState("");
  const [name, setName] = useState("");
  const [selectedSizeIndex, setSelectedSizeIndex] = useState(1); // Default Laptop 680x440
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setUrl("");
      setName("");
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  if (!isOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    let finalUrl = url.trim();
    if (!finalUrl) return;

    // Prepend https:// if not present and not relative
    if (!finalUrl.startsWith("http://") && !finalUrl.startsWith("https://") && !finalUrl.startsWith("/")) {
      finalUrl = "https://" + finalUrl;
    }

    let defaultName = name.trim();
    if (!defaultName) {
      if (finalUrl.includes("netflix.com")) {
        const jbvMatch = finalUrl.match(/[?&]jbv=(\d+)/) || finalUrl.match(/title\/(\d+)/);
        defaultName = jbvMatch ? `Netflix Title #${jbvMatch[1]}` : "Netflix";
      } else {
        try {
          defaultName = new URL(finalUrl, window.location.origin).hostname;
        } catch {
          defaultName = "Website";
        }
      }
    }

    const size = PRESET_SIZES[selectedSizeIndex];
    onAdd(finalUrl, defaultName, size.width, size.height);
    onClose();
  };

  const handleSelectPreset = (presetUrl: string, presetName: string) => {
    setUrl(presetUrl);
    setName(presetName);
  };

  return (
    <div className="ws-modal-backdrop" onClick={onClose}>
      <div
        className="ws-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="modal-title"
      >
        <div className="ws-modal-header">
          <div className="ws-modal-title-wrap">
            <span className="ws-modal-icon-badge">
              <Globe size={18} />
            </span>
            <div>
              <h2 id="modal-title" className="ws-modal-title">
                Add Website to Canvas
              </h2>
              <p className="ws-modal-subtitle">
                Embed a live website as an interactive browser window
              </p>
            </div>
          </div>
          <button
            type="button"
            className="ws-modal-close-btn"
            onClick={onClose}
            aria-label="Close"
          >
            <X size={18} />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="ws-modal-body">
          {/* URL Input */}
          <div className="ws-modal-field">
            <label className="ws-modal-label">Website URL</label>
            <div className="ws-modal-input-wrap">
              <Globe size={15} className="ws-modal-input-icon" />
              <input
                ref={inputRef}
                type="text"
                className="ws-modal-input"
                placeholder="https://example.com or domain.com"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                required
              />
            </div>
          </div>

          {/* Quick Presets */}
          <div className="ws-modal-field">
            <label className="ws-modal-label">Quick Suggestions</label>
            <div className="ws-modal-presets">
              {PRESET_SITES.map((site) => (
                <button
                  key={site.label}
                  type="button"
                  className={`ws-modal-preset-chip ${url === site.url ? "is-active" : ""}`}
                  onClick={() => handleSelectPreset(site.url, site.label)}
                >
                  {site.label}
                </button>
              ))}
            </div>
          </div>

          {/* Window Size Options */}
          <div className="ws-modal-field">
            <label className="ws-modal-label">Viewport Size</label>
            <div className="ws-modal-size-grid">
              {PRESET_SIZES.map((size, idx) => {
                const Icon = size.icon;
                const isSelected = selectedSizeIndex === idx;
                return (
                  <button
                    key={size.label}
                    type="button"
                    className={`ws-modal-size-card ${isSelected ? "is-selected" : ""}`}
                    onClick={() => setSelectedSizeIndex(idx)}
                  >
                    <Icon size={18} />
                    <div className="ws-modal-size-info">
                      <span className="ws-modal-size-name">{size.label}</span>
                      <span className="ws-modal-size-dim">
                        {size.width} × {size.height}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Name / Label */}
          <div className="ws-modal-field">
            <label className="ws-modal-label">Window Title (Optional)</label>
            <input
              type="text"
              className="ws-modal-input plain"
              placeholder="e.g. Design Specs, Documentation"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
          </div>

          {/* Helpful note */}
          <div className="ws-modal-hint">
            <ExternalLink size={13} className="ws-modal-hint-icon" />
            <span>
              Once placed, you can freely move, resize, rotate, and interact with the live page directly on the canvas.
            </span>
          </div>

          {/* Footer actions */}
          <div className="ws-modal-footer">
            <button
              type="button"
              className="ws-modal-btn ws-modal-btn-cancel"
              onClick={onClose}
            >
              Cancel
            </button>
            <button
              type="submit"
              className="ws-modal-btn ws-modal-btn-primary"
              disabled={!url.trim()}
            >
              Add to Canvas
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
