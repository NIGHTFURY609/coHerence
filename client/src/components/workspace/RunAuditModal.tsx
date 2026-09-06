import { useEffect, useMemo, useState } from "react";
import { Sparkles, X } from "lucide-react";
import { toast } from "sonner";
import {
  DEFAULT_GOAL,
  DEFAULT_SUCCESS,
  DEMO_GOAL,
  DEMO_PROFILES,
  DEMO_STEPS,
  DEMO_SUCCESS,
  cancelJob,
  getHealth,
  isDemoCheckout,
  startJob,
} from "@/lib/coherenceApi";
import { cancelAudit, useAuditStore, watchJob } from "@/stores/auditStore";

type Props = {
  isOpen: boolean;
  onClose: () => void;
  url: string;
};

export default function RunAuditModal({ isOpen, onClose, url }: Props) {
  const demo = useMemo(() => isDemoCheckout(url), [url]);
  const [goal, setGoal] = useState(demo ? DEMO_GOAL : DEFAULT_GOAL);
  const [success, setSuccess] = useState(demo ? DEMO_SUCCESS : DEFAULT_SUCCESS);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const running = useAuditStore((s) => s.running);
  const jobId = useAuditStore((s) => s.jobId);

  useEffect(() => {
    if (!isOpen) return;
    setGoal(demo ? DEMO_GOAL : DEFAULT_GOAL);
    setSuccess(demo ? DEMO_SUCCESS : DEFAULT_SUCCESS);
    setError("");
    setBusy(false);
  }, [isOpen, demo, url]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (!(await getHealth())) {
        setError("Lithium is not running. Start: uvicorn lithium.app:app --port 8000");
        setBusy(false);
        return;
      }
      if (running && jobId) {
        await cancelAudit();
      }
      const body = demo
        ? {
            url,
            success_selector: DEMO_SUCCESS,
            steps: DEMO_STEPS,
            profile_ids: DEMO_PROFILES,
            n_trials: 1,
            diagnose: true,
          }
        : {
            url,
            success_selector: success.trim() || DEFAULT_SUCCESS,
            goal: goal.trim() || DEFAULT_GOAL,
            plan_once: true,
            profile_ids: DEMO_PROFILES,
            n_trials: 1,
            diagnose: true,
          };
      let snap;
      try {
        snap = await startJob(body);
      } catch (first) {
        const message = first instanceof Error ? first.message : "";
        const stuck = message.match(/already running \(([^)]+)\)/);
        if (!stuck) throw first;
        await cancelJob(stuck[1]);
        snap = await startJob(body);
      }
      watchJob(snap.job_id);
      toast.success(
        demo
          ? "Playwright is capturing the demo checkout"
          : "Playwright is opening this site",
      );
      onClose();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not start job";
      setError(message);
      toast.error(message);
      setBusy(false);
    }
  };

  return (
    <div className="ws-modal-backdrop" onClick={onClose}>
      <div
        className="ws-modal-card"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-labelledby="audit-title"
      >
        <div className="ws-modal-header">
          <div className="ws-modal-title-wrap">
            <span className="ws-modal-icon-badge">
              <Sparkles size={18} />
            </span>
            <div>
              <h2 id="audit-title" className="ws-modal-title">
                Run fairness audit
              </h2>
              <p className="ws-modal-subtitle">
                Playwright drives each profile. Hydrogen scores. Helium
                (Qwen 27B) writes the diagnosis.
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
          <div className="ws-modal-field">
            <label className="ws-modal-label">Target</label>
            <input className="ws-modal-input plain" value={url} readOnly />
          </div>
          {demo ? (
            <p className="ws-modal-hint">
              Playwright clicks Place order → Pay now (you will see each
              frame). Helium writes the report after. Wikipedia-style sites
              wait on Nitrogen for each click.
            </p>
          ) : (
            <>
              <p className="ws-modal-hint">
                Nitrogen navigates with a goal. Do not use success selector
                &quot;body&quot; — that skips the VL loop.
              </p>
              <div className="ws-modal-field">
                <label className="ws-modal-label">Task goal</label>
                <input
                  className="ws-modal-input plain"
                  placeholder={DEFAULT_GOAL}
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                />
              </div>
              <div className="ws-modal-field">
                <label className="ws-modal-label">Success selector</label>
                <input
                  className="ws-modal-input plain"
                  placeholder="body"
                  value={success}
                  onChange={(e) => setSuccess(e.target.value)}
                />
              </div>
            </>
          )}
          {error ? (
            <p className="ws-modal-hint" style={{ color: "#E8A598" }}>
              {error}
            </p>
          ) : null}
          <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
            <button
              type="submit"
              className="ws-toolbar-audit-btn"
              disabled={busy}
            >
              <Sparkles size={13} />
              <span>
                {busy
                  ? "Starting…"
                  : running
                    ? "Restart capture"
                    : "Start capture"}
              </span>
            </button>
            {running ? (
              <button
                type="button"
                className="ws-toolbar-audit-btn"
                onClick={() => void cancelAudit()}
              >
                <span>Cancel</span>
              </button>
            ) : null}
          </div>
        </form>
      </div>
    </div>
  );
}
