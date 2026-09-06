import { previewUrl } from "@/lib/coherenceApi";
import { useAuditStore } from "@/stores/auditStore";

export default function PlaywrightDock() {
  const audit = useAuditStore();
  if (!audit.jobId) return null;
  if (audit.status === "idle") return null;

  const last = audit.events.at(-1);
  const selector =
    last && typeof last.selector === "string" ? last.selector : "";
  const waitingOnVl =
    audit.status === "running" &&
    (audit.stage === "vl_wait" ||
      (typeof last?.stage === "string" && last.stage === "vl_wait"));
  const failed = audit.status === "error";

  return (
    <aside className="ws-playwright-dock" aria-label="Playwright viewport">
      <div className="ws-playwright-dock-head">
        <strong>Playwright viewport</strong>
        <span>
          {failed
            ? "failed"
            : waitingOnVl
              ? "Nitrogen choosing next click"
              : audit.currentProfile
                ? audit.currentProfile.replaceAll("_", " ")
                : audit.stage || audit.status}
          {!failed && !waitingOnVl && selector ? ` → ${selector}` : ""}
        </span>
      </div>
      {audit.preview ? (
        <img
          alt="Live Chromium frame"
          src={previewUrl(audit.jobId, audit.previewBust)}
        />
      ) : (
        <p className="ws-playwright-dock-wait">
          {failed
            ? "Chromium never got a frame."
            : "Waiting for the first Chromium frame."}
        </p>
      )}
      {failed && audit.error ? (
        <p className="ws-playwright-dock-wait">{audit.error}</p>
      ) : null}
      {!failed && audit.warning ? (
        <p className="ws-playwright-dock-wait">{audit.warning}</p>
      ) : null}
      {waitingOnVl ? (
        <p className="ws-playwright-dock-wait">
          Chromium is paused on this frame while Nitrogen (Qwen VL) picks the
          next action on the B300. Clicks appear after that generate returns.
        </p>
      ) : null}
    </aside>
  );
}
