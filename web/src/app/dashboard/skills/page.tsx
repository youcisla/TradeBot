"use client";

import { useEffect, useState, useCallback } from "react";

interface Skill {
  name: string;
  description: string;
  location: string;
  user_invocable: boolean;
  is_core: boolean;
}

const PANEL: React.CSSProperties = {
  background: "linear-gradient(135deg, #0a0a12 0%, #0d0d18 100%)",
  border: "1px solid #1a1a2e",
  borderRadius: 8,
  padding: 20,
};

const MONO: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
};

const BUTTON: React.CSSProperties = {
  ...MONO,
  fontSize: 11,
  padding: "6px 14px",
  border: "1px solid #1a1a2e",
  borderRadius: 4,
  cursor: "pointer",
  textTransform: "uppercase" as const,
  letterSpacing: "0.08em",
  transition: "all 0.15s",
};

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newContent, setNewContent] = useState("");

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch("/api/skills");
      const data = await res.json();
      setSkills(data.skills || []);
    } catch {
      console.error("Failed to fetch skills");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  const selectSkill = async (name: string) => {
    setSelected(name);
    try {
      const res = await fetch(`/api/skills?name=${encodeURIComponent(name)}`);
      const data = await res.json();
      setContent(data.content || "");
    } catch {
      setContent("Failed to load skill content.");
    }
  };

  const handleCreate = async () => {
    if (!newName || !newDesc || !newContent) return;
    try {
      const res = await fetch("/api/skills", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: newName, description: newDesc, content: newContent }),
      });
      if (res.ok) {
        setCreating(false);
        setNewName("");
        setNewDesc("");
        setNewContent("");
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Creation failed");
      }
    } catch {
      alert("Failed to create skill");
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete skill "${name}"?`)) return;
    try {
      const res = await fetch(`/api/skills?name=${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        if (selected === name) { setSelected(null); setContent(""); }
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Delete failed");
      }
    } catch {
      alert("Failed to delete skill");
    }
  };

  const INPUT: React.CSSProperties = {
    ...MONO,
    fontSize: 12,
    padding: "8px 12px",
    background: "#080810",
    border: "1px solid #1a1a2e",
    borderRadius: 4,
    color: "#c0c8d4",
    width: "100%",
    outline: "none",
  };

  if (loading) {
    return (
      <div style={{ ...MONO, color: "#607888", fontSize: 13, padding: 40 }}>
        Loading skills…
      </div>
    );
  }

  return (
    <div style={{ display: "flex", gap: 20, minHeight: "calc(100vh - 120px)" }}>
      {/* ── Left: Skill list ── */}
      <div style={{ ...PANEL, width: 320, flexShrink: 0, overflowY: "auto" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h2 style={{ ...MONO, fontSize: 13, color: "#00ff88", margin: 0, letterSpacing: "0.1em", textTransform: "uppercase" }}>
            ⚡ Skills ({skills.length})
          </h2>
          <button
            onClick={() => setCreating(!creating)}
            style={{ ...BUTTON, background: creating ? "#1a0a0a" : "#0a1a0a", color: creating ? "#ff4141" : "#00ff88", borderColor: creating ? "#2e1a1a" : "#1a2e1a" }}
          >
            {creating ? "✕ Cancel" : "+ New"}
          </button>
        </div>

        {creating && (
          <div style={{ ...PANEL, background: "#060610", marginBottom: 16, padding: 14 }}>
            <div style={{ marginBottom: 8 }}>
              <label style={{ ...MONO, fontSize: 9, color: "#607888", textTransform: "uppercase", letterSpacing: "0.1em" }}>Name (slug)</label>
              <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="my-new-skill" style={INPUT} />
            </div>
            <div style={{ marginBottom: 8 }}>
              <label style={{ ...MONO, fontSize: 9, color: "#607888", textTransform: "uppercase", letterSpacing: "0.1em" }}>Description</label>
              <input value={newDesc} onChange={(e) => setNewDesc(e.target.value)} placeholder="Description of the skill" style={INPUT} />
            </div>
            <div style={{ marginBottom: 10 }}>
              <label style={{ ...MONO, fontSize: 9, color: "#607888", textTransform: "uppercase", letterSpacing: "0.1em" }}>Content</label>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                placeholder="# Skill content (markdown)"
                rows={4}
                style={{ ...INPUT, resize: "vertical" }}
              />
            </div>
            <button onClick={handleCreate} style={{ ...BUTTON, background: "#0a1a0a", color: "#00ff88", borderColor: "#1a2e1a", width: "100%" }}>
              Create Skill
            </button>
          </div>
        )}

        {skills.map((skill) => (
          <div
            key={skill.name}
            onClick={() => selectSkill(skill.name)}
            style={{
              padding: "10px 12px",
              marginBottom: 4,
              borderRadius: 4,
              cursor: "pointer",
              background: selected === skill.name ? "#0d1a0d" : "transparent",
              borderLeft: selected === skill.name ? "2px solid #00ff88" : "2px solid transparent",
              transition: "all 0.15s",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span style={{ ...MONO, fontSize: 12, color: selected === skill.name ? "#00ff88" : "#c0c8d4", fontWeight: selected === skill.name ? 700 : 400 }}>
                {skill.name}
              </span>
              <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                {skill.is_core && (
                  <span style={{ ...MONO, fontSize: 8, color: "#607888", padding: "2px 5px", background: "#0a0a14", borderRadius: 3, border: "1px solid #1a1a2e", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                    core
                  </span>
                )}
                {!skill.is_core && (
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(skill.name); }}
                    style={{ ...BUTTON, padding: "2px 6px", fontSize: 9, background: "transparent", color: "#5a3030", borderColor: "transparent" }}
                  >
                    ✕
                  </button>
                )}
              </div>
            </div>
            <div style={{ ...MONO, fontSize: 10, color: "#9aa8b8", marginTop: 4, lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {skill.description}
            </div>
          </div>
        ))}
      </div>

      {/* ── Right: Skill content ── */}
      <div style={{ ...PANEL, flex: 1, overflow: "auto" }}>
        {selected ? (
          <>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16, borderBottom: "1px solid #1a1a2e", paddingBottom: 12 }}>
              <h2 style={{ ...MONO, fontSize: 14, color: "#00ff88", margin: 0, letterSpacing: "0.08em" }}>
                {selected}
              </h2>
              <span style={{ ...MONO, fontSize: 9, color: "#607888", letterSpacing: "0.1em", textTransform: "uppercase" }}>
                SKILL.md
              </span>
            </div>
            <pre style={{
              ...MONO,
              fontSize: 12,
              color: "#a0b0c0",
              lineHeight: 1.6,
              whiteSpace: "pre-wrap",
              wordBreak: "break-word",
              margin: 0,
              background: "#060610",
              padding: 16,
              borderRadius: 6,
              border: "1px solid #12121e",
              maxHeight: "calc(100vh - 240px)",
              overflow: "auto",
            }}>
              {content}
            </pre>
          </>
        ) : (
          <div style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            height: "100%",
            minHeight: 300,
          }}>
            <div style={{ textAlign: "center" }}>
              <div style={{ fontSize: 32, marginBottom: 12, opacity: 0.3 }}>⚡</div>
              <div style={{ ...MONO, fontSize: 12, color: "#607888", letterSpacing: "0.1em" }}>
                SELECT A SKILL TO VIEW
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
