import { useWorkspaceStore } from "@/stores/workspaceStore";
import { useAuditStore } from "@/stores/auditStore";

const toolLabels: Record<string, string> = {
  select: "Select",
  hand: "Hand",
  frame: "Frame",
  rectangle: "Rectangle",
  ellipse: "Ellipse",
  line: "Line",
  arrow: "Arrow",
  text: "Text",
  image: "Image",
};

export default function WorkspaceStatusbar() {
  const { elements, selectedIds, activeTool, canvas } = useWorkspaceStore();
  const audit = useAuditStore();

  return (
    <footer className="ws-statusbar">
      <div className="ws-statusbar-section">
        <span className="ws-statusbar-dot" />
        <span>{elements.length} elements</span>
        {selectedIds.length > 0 && (
          <span>· {selectedIds.length} selected</span>
        )}
      </div>
      <div className="ws-statusbar-section">
        <span>
          {audit.apiOnline === false
            ? "API offline · uvicorn lithium.app:app --port 8000"
            : audit.status === "error"
              ? `Audit failed${audit.error ? ` · ${audit.error}` : ""}`
              : audit.status === "running"
              ? `Audit · ${audit.currentProfile || audit.stage || "running"}`
              : audit.stage === "diagnose"
                ? "Helium · writing report"
                : audit.status === "done" && audit.report
                  ? `${audit.report.analyst === "helium" ? "Helium" : "Hydrogen"} · ${audit.report.overall_fairness_score ?? "—"}/100`
                : (toolLabels[activeTool] ?? activeTool)}
        </span>
      </div>
      <div className="ws-statusbar-section">
        <span>{Math.round(canvas.zoom * 100)}%</span>
      </div>
    </footer>
  );
}
