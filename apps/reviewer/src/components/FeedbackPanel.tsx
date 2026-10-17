import React, { useState } from "react";
import type { RevisionOpsFile, RevisionOp, RevisionComment } from "../types/schemas";

interface FeedbackPanelProps {
  projectName: string;
  optionId: string;
  planVersion: number;
  selectedId: string | null;
}

export const FeedbackPanel: React.FC<FeedbackPanelProps> = ({
  projectName,
  optionId,
  planVersion,
  selectedId,
}) => {
  const [verbatimRequest, setVerbatimRequest] = useState<string>("");
  const [author, setAuthor] = useState<string>("homeowner:owner");
  const [comments, setComments] = useState<RevisionComment[]>([]);
  const [operations, setOperations] = useState<RevisionOp[]>([]);

  // Form states for new comment / op
  const [commentText, setCommentText] = useState<string>("");
  const [opType, setOpType] = useState<string>("area");
  const [opTarget, setOpTarget] = useState<string>(selectedId || "pi-kitchen");
  const [opValue, setOpValue] = useState<string>("18.0");

  const handleAddComment = () => {
    if (!commentText.trim()) return;
    const newComment: RevisionComment = {
      id: `c-${Date.now().toString(36)}`,
      element_id: selectedId || "plan",
      text: commentText.trim(),
      created_at: new Date().toISOString(),
    };
    setComments((prev) => [...prev, newComment]);
    setCommentText("");
  };

  const handleAddOperation = () => {
    if (!opTarget.trim()) return;
    let parsedVal: string | number | null = opValue.trim();
    if (opType === "area") {
      const num = parseFloat(parsedVal);
      if (!isNaN(num)) parsedVal = num;
    }
    const newOp: RevisionOp = {
      op_type: opType,
      target: opTarget.trim(),
      value: parsedVal || null,
    };
    setOperations((prev) => [...prev, newOp]);
  };

  const handleExportJson = () => {
    const opsFile: RevisionOpsFile = {
      schema_version: "1.0.0",
      project: projectName,
      option: optionId,
      plan_version: planVersion,
      verbatim_request: verbatimRequest.trim() || "Homeowner feedback export",
      author: author.trim() || "homeowner:owner",
      created_at: new Date().toISOString(),
      operations,
      comments,
    };

    const blob = new Blob([JSON.stringify(opsFile, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `revision_ops_${optionId}_v${planVersion}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div
      data-testid="feedback-panel"
      style={{
        padding: 16,
        background: "#1e293b",
        color: "#f8fafc",
        fontSize: 12,
        display: "flex",
        flexDirection: "column",
        gap: 16,
      }}
    >
      <div style={{ fontWeight: 700, fontSize: 14, color: "#38bdf8" }}>
        Feedback & Structured Revision Ops
      </div>

      {/* Author and Verbatim Request Input */}
      <div>
        <div style={{ marginBottom: 8 }}>
          <label style={{ display: "block", color: "#94a3b8", marginBottom: 4 }}>
            Author (Actor identifier):
          </label>
          <input
            data-testid="author-input"
            value={author}
            onChange={(e) => setAuthor(e.target.value)}
            placeholder="e.g. homeowner:owner"
            style={{
              width: "100%",
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 4,
              color: "#f8fafc",
              padding: "6px 8px",
              fontSize: 12,
              boxSizing: "border-box",
            }}
          />
        </div>
        <label style={{ display: "block", color: "#94a3b8", marginBottom: 4 }}>
          Overall Request (Homeowner Verbatim Words):
        </label>
        <textarea
          data-testid="verbatim-request-input"
          value={verbatimRequest}
          onChange={(e) => setVerbatimRequest(e.target.value)}
          placeholder="e.g. Enlarge kitchen to 18 m² and separate from living room"
          rows={2}
          style={{
            width: "100%",
            background: "#0f172a",
            border: "1px solid #334155",
            borderRadius: 4,
            color: "#f8fafc",
            padding: 8,
            fontSize: 12,
          }}
        />
      </div>

      {/* Entity-Linked Comment */}
      <div style={{ borderTop: "1px solid #334155", paddingTop: 12 }}>
        <div style={{ fontWeight: 600, color: "#cbd5e1", marginBottom: 6 }}>
          Attach Comment to Element:
        </div>
        <div style={{ color: "#38bdf8", marginBottom: 4, fontFamily: "monospace" }}>
          Target: {selectedId || "Entire Plan"}
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <input
            type="text"
            data-testid="comment-input"
            value={commentText}
            onChange={(e) => setCommentText(e.target.value)}
            placeholder="Comment on selected element..."
            style={{
              flex: 1,
              background: "#0f172a",
              border: "1px solid #334155",
              borderRadius: 4,
              color: "#f8fafc",
              padding: "6px 8px",
              fontSize: 12,
            }}
          />
          <button
            onClick={handleAddComment}
            style={{
              background: "#334155",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              padding: "6px 12px",
              cursor: "pointer",
            }}
          >
            Add
          </button>
        </div>
        {comments.length > 0 && (
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {comments.map((c) => (
              <div
                key={c.id}
                style={{ background: "#0f172a", padding: "4px 8px", borderRadius: 4, fontSize: 11 }}
              >
                <span style={{ color: "#38bdf8", fontFamily: "monospace" }}>{c.element_id}:</span> {c.text}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Revision Operations Builder */}
      <div style={{ borderTop: "1px solid #334155", paddingTop: 12 }}>
        <div style={{ fontWeight: 600, color: "#cbd5e1", marginBottom: 6 }}>
          Structured Operation (--area, --separate, --level):
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 6, alignItems: "center" }}>
          <select
            value={opType}
            onChange={(e) => setOpType(e.target.value)}
            style={{
              background: "#0f172a",
              border: "1px solid #334155",
              color: "#fff",
              padding: "6px 4px",
              borderRadius: 4,
            }}
          >
            <option value="area">--area</option>
            <option value="separate">--separate</option>
            <option value="adjacent">--adjacent</option>
            <option value="level">--level</option>
            <option value="rethink">--rethink</option>
          </select>
          <input
            type="text"
            data-testid="op-target-input"
            value={opTarget}
            onChange={(e) => setOpTarget(e.target.value)}
            placeholder="Target room"
            style={{
              background: "#0f172a",
              border: "1px solid #334155",
              color: "#fff",
              padding: "6px 8px",
              borderRadius: 4,
            }}
          />
          <input
            type="text"
            data-testid="op-value-input"
            value={opValue}
            onChange={(e) => setOpValue(e.target.value)}
            placeholder="Value"
            style={{
              background: "#0f172a",
              border: "1px solid #334155",
              color: "#fff",
              padding: "6px 8px",
              borderRadius: 4,
            }}
          />
          <button
            data-testid="add-op-btn"
            onClick={handleAddOperation}
            style={{
              background: "#0284c7",
              color: "#fff",
              border: "none",
              borderRadius: 4,
              padding: "6px 10px",
              cursor: "pointer",
              fontWeight: 600,
            }}
          >
            Add
          </button>
        </div>
        {operations.length > 0 && (
          <div style={{ marginTop: 8, display: "flex", flexDirection: "column", gap: 4 }}>
            {operations.map((op, idx) => (
              <div
                key={idx}
                style={{
                  background: "#0f172a",
                  padding: "4px 8px",
                  borderRadius: 4,
                  fontFamily: "monospace",
                  color: "#4ade80",
                }}
              >
                {op.op_type}:{op.target}{op.value ? `=${op.value}` : ""}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Export Button */}
      <div style={{ borderTop: "1px solid #334155", paddingTop: 12 }}>
        <button
          data-testid="export-ops-button"
          onClick={handleExportJson}
          style={{
            width: "100%",
            background: "#22c55e",
            color: "#0f172a",
            fontWeight: 700,
            border: "none",
            borderRadius: 6,
            padding: "10px 16px",
            cursor: "pointer",
            fontSize: 13,
          }}
        >
          ⬇ Export revision_ops.json
        </button>
        <div style={{ color: "#94a3b8", fontSize: 10, marginTop: 6, textAlign: "center" }}>
          Replay via: <code>house-ai plan revise-from-file &lt;project&gt; &lt;file&gt;</code>
        </div>
      </div>
    </div>
  );
};
