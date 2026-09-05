import { useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  ClipboardPaste,
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Copy,
  Crop,
  Download,
  Eye,
  FileText,
  ImagePlus,
  Layers3,
  Plus,
  Settings2,
  Scissors,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  Type,
  Upload,
} from "lucide-react";

type Profile = "baseline_default" | "motor_impaired" | "keyboard_only";

const profiles: { id: Profile; label: string; tone: string }[] = [
  { id: "baseline_default", label: "Baseline user", tone: "clay" },
  { id: "motor_impaired", label: "Motor impaired", tone: "blue" },
  { id: "keyboard_only", label: "Keyboard only", tone: "pistachio" },
];

type EditorItem = {
  id: string;
  label: string;
  kind: "text" | "image";
  x: number;
  y: number;
  width: number;
  height: number;
  text?: string;
  src?: string;
  crop?: number;
};

const layerIcon = (kind: EditorItem["kind"]) => {
  if (kind === "image") return ImagePlus;
  if (kind === "text") return Type;
  return Layers3;
};

export default function Workshop() {
  const [profile, setProfile] = useState<Profile>("baseline_default");
  const [inspectorTab, setInspectorTab] = useState<"inspect" | "layers">("inspect");
  const [zoom, setZoom] = useState(67);
  const [items, setItems] = useState<EditorItem[]>([]);
  const [selectedId, setSelectedId] = useState("");
  const [clipboardItem, setClipboardItem] = useState<EditorItem | null>(null);
  const dragRef = useRef<{ id: string; startX: number; startY: number; itemX: number; itemY: number } | null>(null);
  const artboardRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const resizeRef = useRef<{ id: string; startX: number; startY: number; width: number; height: number } | null>(null);
  const activeProfile = profiles.find((item) => item.id === profile) ?? profiles[0];
  const selectedItem = items.find((item) => item.id === selectedId);

  const updateItem = (id: string, update: Partial<EditorItem>) => {
    setItems((current) => current.map((item) => item.id === id ? { ...item, ...update } : item));
  };

  const addTextLayer = () => {
    const id = `text-${Date.now()}`;
    setItems((current) => [...current, { id, label: "New text", kind: "text", x: 110, y: 430, width: 180, height: 36, text: "New field note" }]);
    setSelectedId(id);
  };

  const addImages = (files: FileList | null) => {
    if (!files?.length) return;
    const additions = Array.from(files).map((file, index) => ({
      id: `image-${Date.now()}-${index}`,
      label: file.name.replace(/\.[^/.]+$/, "") || "Image",
      kind: "image" as const,
      x: 220 + (index % 3) * 22,
      y: 150 + (index % 3) * 22,
      width: 240,
      height: 180,
      src: URL.createObjectURL(file),
      crop: 0,
    }));
    setItems((current) => [...current, ...additions]);
    setSelectedId(additions[0].id);
  };

  const deleteSelected = () => {
    if (!selectedItem) return;
    setItems((current) => current.filter((item) => item.id !== selectedItem.id));
    setSelectedId("");
  };

  const pasteItem = () => {
    if (!clipboardItem) return;
    const pasted = { ...clipboardItem, id: `${clipboardItem.id}-paste-${Date.now()}`, label: `${clipboardItem.label} copy`, x: clipboardItem.x + 18, y: clipboardItem.y + 18 };
    setItems((current) => [...current, pasted]);
    setSelectedId(pasted.id);
  };

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (document.activeElement?.tagName === "INPUT" || !selectedItem) return;
      if ((event.key === "Delete" || event.key === "Backspace")) {
        event.preventDefault();
        deleteSelected();
        return;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "d") {
        event.preventDefault();
        const copy = { ...selectedItem, id: `${selectedItem.id}-copy-${Date.now()}`, label: `${selectedItem.label} copy`, x: selectedItem.x + 16, y: selectedItem.y + 16 };
        setItems((current) => [...current, copy]);
        setSelectedId(copy.id);
        return;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "x") {
        event.preventDefault();
        setClipboardItem(selectedItem);
        setItems((current) => current.filter((item) => item.id !== selectedItem.id));
        setSelectedId("");
        return;
      }
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "v") {
        event.preventDefault();
        pasteItem();
        return;
      }
      const nudge = event.shiftKey ? 10 : 1;
      if (event.key === "ArrowLeft" || event.key === "ArrowRight" || event.key === "ArrowUp" || event.key === "ArrowDown") {
        event.preventDefault();
        updateItem(selectedItem.id, { x: selectedItem.x + (event.key === "ArrowLeft" ? -nudge : event.key === "ArrowRight" ? nudge : 0), y: selectedItem.y + (event.key === "ArrowUp" ? -nudge : event.key === "ArrowDown" ? nudge : 0) });
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [selectedItem, clipboardItem]);

  const startDrag = (event: React.PointerEvent, item: EditorItem) => {
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    setSelectedId(item.id);
    dragRef.current = { id: item.id, startX: event.clientX, startY: event.clientY, itemX: item.x, itemY: item.y };
  };

  const moveDrag = (event: React.PointerEvent) => {
    const drag = dragRef.current;
    if (!drag || !artboardRef.current) return;
    const bounds = artboardRef.current.getBoundingClientRect();
    updateItem(drag.id, { x: Math.max(0, Math.min(bounds.width - 40, drag.itemX + event.clientX - drag.startX)), y: Math.max(0, Math.min(bounds.height - 30, drag.itemY + event.clientY - drag.startY)) });
  };

  const endDrag = () => { dragRef.current = null; };

  const startResize = (event: React.PointerEvent<HTMLSpanElement>, item: EditorItem) => {
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    setSelectedId(item.id);
    resizeRef.current = { id: item.id, startX: event.clientX, startY: event.clientY, width: item.width, height: item.height };
  };

  const moveResize = (event: React.PointerEvent) => {
    const resize = resizeRef.current;
    if (!resize) return;
    updateItem(resize.id, { width: Math.max(80, resize.width + event.clientX - resize.startX), height: Math.max(60, resize.height + event.clientY - resize.startY) });
  };

  const endPointerInteraction = () => { dragRef.current = null; resizeRef.current = null; };

  return (
    <div className="workshop-shell">
      <header className="workshop-topbar">
        <a className="workshop-brand" href="/" aria-label="Return to CoHERence home">
          <span className="workshop-brand-mark">C</span>
          <span>Co<span>HER</span>ence <small>/ workshop</small></span>
        </a>
        <div className="workshop-file"><FileText size={14} /> Untitled field study <span>Saved just now</span></div>
        <div className="workshop-top-actions">
          <button type="button" className="workshop-icon-button" aria-label="Help"><CircleHelp size={17} /></button>
          <button type="button" className="workshop-icon-button" aria-label="Settings"><Settings2 size={17} /></button>
          <button type="button" className="workshop-share"><Upload size={14} /> Share</button>
        </div>
      </header>

      <div className="workshop-body">
        <aside className="workshop-rail" aria-label="Workshop navigation">
          <div className="workshop-rail-tools">
            <button type="button" className="workshop-rail-button is-current" aria-label="Files"><FileText size={18} /></button>
            <button type="button" className="workshop-rail-button" aria-label="Assets"><Layers3 size={18} /></button>
            <button type="button" className="workshop-rail-button" aria-label="Insights"><Sparkles size={18} /></button>
          </div>
          <a className="workshop-back" href="/" aria-label="Back to home"><ArrowLeft size={18} /></a>
        </aside>

        <aside className="workshop-layers">
          <div className="workshop-panel-heading"><span>Workspace</span><button type="button" aria-label="Add media" onClick={() => fileInputRef.current?.click()}><Plus size={16} /></button></div>
          <div className="workshop-add-actions">
            <button type="button" onClick={addTextLayer}><Type size={13} /> Text</button>
            <input ref={fileInputRef} type="file" accept="image/*" multiple hidden onChange={(event) => { addImages(event.target.files); event.currentTarget.value = ""; }} />
          </div>
          <div className="workshop-panel-heading workshop-layers-heading"><span>Layers</span><button type="button" aria-label="Layer options"><SlidersHorizontal size={15} /></button></div>
          <div className="workshop-layer-list">
            {items.map((item) => {
              const Icon = layerIcon(item.kind);
              return <button type="button" className={`workshop-layer ${selectedId === item.id ? "is-selected" : ""}`} key={item.id} onClick={() => setSelectedId(item.id)}><Icon size={15} /><span>{item.label}</span><Eye size={14} /></button>;
            })}
          </div>
          {items.length === 0 && <div className="workshop-empty-layers">No layers yet.<br />Import files to begin.</div>}
          <div className="workshop-layer-note"><span className="workshop-status-dot" />Live prototype</div>
        </aside>

        <main className="workshop-canvas-area">
          <div className="workshop-canvas-toolbar">
            <div className="workshop-edit-actions"><button type="button" title="Cut selected" disabled={!selectedItem} onClick={() => { if (selectedItem) { setClipboardItem(selectedItem); setItems((current) => current.filter((item) => item.id !== selectedItem.id)); setSelectedId(""); } }}><Scissors size={14} /></button><button type="button" title="Copy selected" disabled={!selectedItem} onClick={() => selectedItem && setClipboardItem(selectedItem)}><Copy size={14} /></button><button type="button" title="Paste layer" disabled={!clipboardItem} onClick={pasteItem}><ClipboardPaste size={14} /></button></div>
            <div className="workshop-canvas-meta"><span>Desktop / 1440</span><span className="workshop-divider" /><button type="button" onClick={() => setZoom((value) => value >= 100 ? 50 : value + 17)}>{zoom}% <ChevronDown size={13} /></button></div>
          </div>
          <div className="workshop-canvas" onPointerMove={(event) => { moveDrag(event); moveResize(event); }} onPointerUp={endPointerInteraction} onPointerCancel={endPointerInteraction}>
            <div className="workshop-artboard-label">FIELD STUDY / 01</div>
            <div className="workshop-artboard" ref={artboardRef} onPointerDown={() => setSelectedId("")}>
              {items.filter((item) => item.kind === "text").map((item) => <div key={item.id} className={`workshop-editable workshop-added-text ${selectedId === item.id ? "is-selected" : ""}`} style={{ left: item.x, top: item.y, width: item.width, height: item.height }} onPointerDown={(event) => startDrag(event, item)}>{item.text}</div>)}
              {items.filter((item) => item.kind === "image" && item.src).map((item) => <div key={item.id} className={`workshop-editable workshop-image-layer ${selectedId === item.id ? "is-selected" : ""}`} style={{ left: item.x, top: item.y, width: item.width, height: item.height }} onPointerDown={(event) => startDrag(event, item)}><img src={item.src} alt={item.label} onLoad={(event) => { const image = event.currentTarget; if (image.naturalWidth && image.naturalHeight && item.width === 240 && item.height === 180) { const width = Math.min(320, image.naturalWidth); updateItem(item.id, { width, height: Math.round(width * image.naturalHeight / image.naturalWidth) }); } }} style={{ inset: `${-(item.crop ?? 0)}%`, width: `${100 + (item.crop ?? 0) * 2}%`, height: `${100 + (item.crop ?? 0) * 2}%` }} />{selectedId === item.id && <span className="workshop-resize-handle" onPointerDown={(event) => startResize(event, item)} aria-label="Resize media" />}</div>)}
            </div>
          </div>
          <div className="workshop-statusbar"><span><span className="workshop-status-dot" /> Prototype ready</span><span>Click and drag an element to move it</span></div>
        </main>

        <aside className="workshop-inspector">
          <div className="workshop-inspector-tabs"><button type="button" className={inspectorTab === "inspect" ? "is-active" : ""} onClick={() => setInspectorTab("inspect")}>Inspect</button><button type="button" className={inspectorTab === "layers" ? "is-active" : ""} onClick={() => setInspectorTab("layers")}>Prototype</button></div>
          {inspectorTab === "inspect" ? <>
            <div className="workshop-inspector-title"><div><span className="workshop-eyebrow">Selected layer</span><h2>{selectedItem?.label ?? "Nothing selected"}</h2></div><button type="button" className="workshop-icon-button" aria-label="Delete selected layer" onClick={deleteSelected} disabled={!selectedItem}><Trash2 size={16} /></button></div>
            {selectedItem && <>
            <div className="workshop-inspector-section"><div className="workshop-section-label">Layer name <span>Editable</span></div><input className="workshop-name-input" value={selectedItem.label} onChange={(event) => updateItem(selectedItem.id, { label: event.target.value })} /></div>
            <div className="workshop-inspector-section"><div className="workshop-section-label">Position <span>Drag or edit</span></div><div className="workshop-input-grid"><label>X <input type="number" value={Math.round(selectedItem.x)} onChange={(event) => updateItem(selectedItem.id, { x: Number(event.target.value) })} /></label><label>Y <input type="number" value={Math.round(selectedItem.y)} onChange={(event) => updateItem(selectedItem.id, { y: Number(event.target.value) })} /></label><label>W <input type="number" value={Math.round(selectedItem.width)} onChange={(event) => updateItem(selectedItem.id, { width: Number(event.target.value) })} /></label><label>H <input type="number" value={Math.round(selectedItem.height)} onChange={(event) => updateItem(selectedItem.id, { height: Number(event.target.value) })} /></label></div></div>
            {selectedItem.kind === "text" && <div className="workshop-inspector-section"><div className="workshop-section-label">Content <span>Editable</span></div><textarea className="workshop-content-input" value={selectedItem.text ?? ""} onChange={(event) => updateItem(selectedItem.id, { text: event.target.value })} /></div>}
            {selectedItem.kind === "image" && <div className="workshop-inspector-section"><div className="workshop-section-label">Crop <span>{selectedItem.crop ?? 0}%</span></div><div className="workshop-crop-controls"><Crop size={14} /><input type="range" min="0" max="30" value={selectedItem.crop ?? 0} onChange={(event) => updateItem(selectedItem.id, { crop: Number(event.target.value) })} /></div></div>}
            </>}
            <div className="workshop-inspector-section"><div className="workshop-section-label">Test profile <span>3 active</span></div><div className="workshop-profile-list">{profiles.map((item) => <button type="button" key={item.id} className={`workshop-profile ${profile === item.id ? "is-active" : ""}`} onClick={() => setProfile(item.id)}><span className={`workshop-profile-dot ${item.tone}`} />{item.label}<ChevronRight size={14} /></button>)}</div></div>
          </> : <div className="workshop-prototype-panel"><Sparkles size={21} /><h2>Prototype flow</h2><p>Test how each profile moves through the frame and where the route becomes harder to follow.</p><button type="button" className="workshop-text-button" onClick={() => setInspectorTab("inspect")}>Back to inspect <ChevronRight size={14} /></button></div>}
          <div className="workshop-inspector-footer"><span className={`workshop-profile-dot ${activeProfile.tone}`} /> Testing as {activeProfile.label}</div>
        </aside>
      </div>
    </div>
  );
}
