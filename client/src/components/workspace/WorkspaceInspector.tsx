import { useCallback } from "react";
import {
  useWorkspaceStore,
  type WorkspaceElement,
  type ElementType,
} from "@/stores/workspaceStore";
import {
  Square,
  Circle,
  Type,
  ImagePlus,
  SquareDashed,
  Minus,
  MousePointer2,
  ArrowUpToLine,
  ArrowUp,
  ArrowDown,
  ArrowDownToLine,
  AlignStartVertical,
  AlignCenterVertical,
  AlignEndVertical,
  AlignStartHorizontal,
  AlignCenterHorizontal,
  AlignEndHorizontal,
  AlignLeft,
  AlignCenter,
  AlignRight,
} from "lucide-react";

const typeIcons: Record<ElementType, typeof Square> = {
  rectangle: Square,
  ellipse: Circle,
  text: Type,
  image: ImagePlus,
  frame: SquareDashed,
  line: Minus,
};

function NumberField({
  label,
  value,
  onChange,
  step = 1,
  min,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <div className="ws-number-input">
      <label>{label}</label>
      <input
        type="number"
        value={Math.round(value * 100) / 100}
        step={step}
        min={min}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    </div>
  );
}

function ColorField({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const displayValue =
    value === "transparent" ? "#000000" : value;
  return (
    <div className="ws-color-input">
      <input
        type="color"
        className="ws-color-swatch"
        value={displayValue}
        onChange={(e) => onChange(e.target.value)}
      />
      <input
        className="ws-color-hex"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder="#000000"
      />
    </div>
  );
}

export default function WorkspaceInspector() {
  const {
    elements,
    selectedIds,
    updateElement,
    pushHistory,
    renameElement,
    bringToFront,
    bringForward,
    sendBackward,
    sendToBack,
    alignElements,
    distributeElements,
  } = useWorkspaceStore();

  const selected = elements.filter((e) => selectedIds.includes(e.id));
  const el = selected.length === 1 ? selected[0] : null;

  const update = useCallback(
    (changes: Partial<WorkspaceElement>) => {
      if (!el) return;
      pushHistory();
      updateElement(el.id, changes);
    },
    [el, pushHistory, updateElement],
  );

  if (selected.length === 0) {
    return (
      <aside className="ws-inspector">
        <div className="ws-inspector-empty">
          <MousePointer2 size={32} />
          <p>Select an element to<br />inspect its properties</p>
        </div>
      </aside>
    );
  }

  // Multi-select: only show alignment and ordering
  if (!el) {
    return (
      <aside className="ws-inspector">
        <div className="ws-inspector-header">
          <span className="ws-layer-icon"><Square size={16} /></span>
          <span style={{ fontSize: 13, fontWeight: 700 }}>
            {selected.length} elements selected
          </span>
        </div>

        <div className="ws-inspector-section">
          <div className="ws-inspector-label">Align</div>
          <div className="ws-align-buttons">
            <button type="button" title="Align Left" onClick={() => alignElements("left")}><AlignStartVertical size={14} /></button>
            <button type="button" title="Center H" onClick={() => alignElements("centerH")}><AlignCenterVertical size={14} /></button>
            <button type="button" title="Align Right" onClick={() => alignElements("right")}><AlignEndVertical size={14} /></button>
            <button type="button" title="Align Top" onClick={() => alignElements("top")}><AlignStartHorizontal size={14} /></button>
            <button type="button" title="Center V" onClick={() => alignElements("centerV")}><AlignCenterHorizontal size={14} /></button>
            <button type="button" title="Align Bottom" onClick={() => alignElements("bottom")}><AlignEndHorizontal size={14} /></button>
          </div>
          <div className="ws-align-buttons" style={{ marginTop: 6 }}>
            <button type="button" title="Distribute H" onClick={() => distributeElements("horizontal")} style={{ width: "auto", padding: "0 8px", fontSize: 9 }}>Distribute H</button>
            <button type="button" title="Distribute V" onClick={() => distributeElements("vertical")} style={{ width: "auto", padding: "0 8px", fontSize: 9 }}>Distribute V</button>
          </div>
        </div>

        <div className="ws-inspector-section">
          <div className="ws-inspector-label">Layer order</div>
          <div className="ws-align-buttons">
            <button type="button" title="Bring to Front" onClick={bringToFront}><ArrowUpToLine size={14} /></button>
            <button type="button" title="Bring Forward" onClick={bringForward}><ArrowUp size={14} /></button>
            <button type="button" title="Send Backward" onClick={sendBackward}><ArrowDown size={14} /></button>
            <button type="button" title="Send to Back" onClick={sendToBack}><ArrowDownToLine size={14} /></button>
          </div>
        </div>
      </aside>
    );
  }

  const Icon = typeIcons[el.type];

  return (
    <aside className="ws-inspector">
      {/* Header */}
      <div className="ws-inspector-header">
        <span className="ws-layer-icon"><Icon size={16} /></span>
        <input
          value={el.name}
          onChange={(e) => renameElement(el.id, e.target.value)}
        />
      </div>

      {/* Transform */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-label">Transform</div>
        <div className="ws-input-grid">
          <NumberField label="X" value={el.x} onChange={(v) => update({ x: v })} />
          <NumberField label="Y" value={el.y} onChange={(v) => update({ y: v })} />
          <NumberField label="W" value={el.width} onChange={(v) => update({ width: v })} min={1} />
          <NumberField label="H" value={el.height} onChange={(v) => update({ height: v })} min={1} />
        </div>
        <div style={{ marginTop: 6 }}>
          <NumberField label="R" value={el.rotation} onChange={(v) => update({ rotation: v })} />
        </div>
      </div>

      {/* Appearance */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-label">Fill</div>
        <ColorField value={el.fill} onChange={(v) => update({ fill: v })} />
        <div className="ws-inspector-row" style={{ marginTop: 8 }}>
          <span style={{ fontSize: 10, color: "rgba(247,241,231,.4)", minWidth: 50 }}>Opacity</span>
          <input
            type="range"
            className="ws-slider-input"
            min={0}
            max={100}
            value={Math.round(el.fillOpacity * 100)}
            onChange={(e) => update({ fillOpacity: Number(e.target.value) / 100 })}
          />
          <span style={{ fontSize: 10, minWidth: 28 }}>{Math.round(el.fillOpacity * 100)}%</span>
        </div>
      </div>

      <div className="ws-inspector-section">
        <div className="ws-inspector-label">Stroke</div>
        <ColorField value={el.stroke} onChange={(v) => update({ stroke: v })} />
        <div style={{ marginTop: 8 }}>
          <NumberField label="W" value={el.strokeWidth} onChange={(v) => update({ strokeWidth: v })} min={0} />
        </div>
      </div>

      {/* Corner Radius (rect/frame) */}
      {(el.type === "rectangle" || el.type === "frame") && (
        <div className="ws-inspector-section">
          <div className="ws-inspector-label">Corner radius</div>
          <NumberField label="R" value={el.cornerRadius} onChange={(v) => update({ cornerRadius: v })} min={0} />
        </div>
      )}

      {/* Opacity */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-label">Opacity</div>
        <div className="ws-inspector-row">
          <input
            type="range"
            className="ws-slider-input"
            min={0}
            max={100}
            value={Math.round(el.opacity * 100)}
            onChange={(e) => update({ opacity: Number(e.target.value) / 100 })}
          />
          <span style={{ fontSize: 10, minWidth: 28 }}>{Math.round(el.opacity * 100)}%</span>
        </div>
      </div>

      {/* Typography (text only) */}
      {el.type === "text" && (
        <div className="ws-inspector-section">
          <div className="ws-inspector-label">Typography</div>
          <div className="ws-inspector-row">
            <select
              className="ws-select-input"
              value={el.fontFamily ?? "Manrope"}
              onChange={(e) => update({ fontFamily: e.target.value })}
            >
              <option value="Manrope">Manrope</option>
              <option value="Fraunces">Fraunces</option>
              <option value="Inter">Inter</option>
              <option value="system-ui">System</option>
              <option value="monospace">Monospace</option>
            </select>
          </div>
          <div className="ws-input-grid" style={{ marginTop: 6 }}>
            <NumberField label="Sz" value={el.fontSize ?? 18} onChange={(v) => update({ fontSize: v })} min={1} />
            <div className="ws-number-input">
              <label>Wt</label>
              <select
                className="ws-select-input"
                value={el.fontWeight ?? 500}
                onChange={(e) => update({ fontWeight: Number(e.target.value) })}
              >
                <option value={300}>Light</option>
                <option value={400}>Regular</option>
                <option value={500}>Medium</option>
                <option value={600}>Semi</option>
                <option value={700}>Bold</option>
                <option value={800}>Extra</option>
              </select>
            </div>
          </div>
          <div className="ws-text-align-buttons" style={{ marginTop: 8 }}>
            <button type="button" className={el.textAlign === "left" ? "active" : ""} onClick={() => update({ textAlign: "left" })}><AlignLeft size={14} /></button>
            <button type="button" className={el.textAlign === "center" ? "active" : ""} onClick={() => update({ textAlign: "center" })}><AlignCenter size={14} /></button>
            <button type="button" className={el.textAlign === "right" ? "active" : ""} onClick={() => update({ textAlign: "right" })}><AlignRight size={14} /></button>
          </div>
          <div className="ws-input-grid" style={{ marginTop: 8 }}>
            <NumberField label="LH" value={el.lineHeight ?? 1.5} onChange={(v) => update({ lineHeight: v })} step={0.1} />
            <NumberField label="LS" value={el.letterSpacing ?? 0} onChange={(v) => update({ letterSpacing: v })} step={0.5} />
          </div>
          <div style={{ marginTop: 8 }}>
            <div className="ws-inspector-label">Text color</div>
            <ColorField value={el.textColor ?? "#173B36"} onChange={(v) => update({ textColor: v })} />
          </div>
        </div>
      )}

      {/* Image */}
      {el.type === "image" && (
        <div className="ws-inspector-section">
          <div className="ws-inspector-label">Image</div>
          <input
            className="ws-color-hex"
            style={{ width: "100%" }}
            value={el.src ?? ""}
            placeholder="Image URL"
            onChange={(e) => update({ src: e.target.value })}
          />
          <div className="ws-inspector-row" style={{ marginTop: 8 }}>
            <select
              className="ws-select-input"
              value={el.objectFit ?? "cover"}
              onChange={(e) => update({ objectFit: e.target.value as "cover" | "contain" | "fill" })}
            >
              <option value="cover">Cover</option>
              <option value="contain">Contain</option>
              <option value="fill">Fill</option>
            </select>
          </div>
        </div>
      )}

      {/* Layer order */}
      <div className="ws-inspector-section">
        <div className="ws-inspector-label">Layer order</div>
        <div className="ws-align-buttons">
          <button type="button" title="Bring to Front" onClick={bringToFront}><ArrowUpToLine size={14} /></button>
          <button type="button" title="Bring Forward" onClick={bringForward}><ArrowUp size={14} /></button>
          <button type="button" title="Send Backward" onClick={sendBackward}><ArrowDown size={14} /></button>
          <button type="button" title="Send to Back" onClick={sendToBack}><ArrowDownToLine size={14} /></button>
        </div>
      </div>
    </aside>
  );
}
