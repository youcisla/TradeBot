"use client";

import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";

interface Skill {
  name: string;
  description: string;
  location: string;
  user_invocable: boolean;
  is_core: boolean;
  last_modified?: string;
}

const MONO: React.CSSProperties = {
  fontFamily: "'JetBrains Mono', monospace",
};

const PANEL: React.CSSProperties = {
  background: "#0a0a12",
  border: "1px solid #1c1c28",
  borderRadius: 8,
  padding: 20,
};

function TerminalInput({
  value,
  onChange,
  placeholder,
  style,
}: {
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  style?: React.CSSProperties;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <input
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      placeholder={placeholder}
      style={{
        ...MONO,
        fontSize: 11.5,
        padding: "8px 12px",
        background: "#06060c",
        border: `1px solid ${focused ? "#00ff88" : "#1c1c28"}`,
        borderRadius: 4,
        color: "#c0ccd8",
        width: "100%",
        outline: "none",
        boxSizing: "border-box",
        boxShadow: focused ? "0 0 0 2px rgba(0,255,136,0.14)" : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
        ...style,
      }}
    />
  );
}

function TerminalTextarea({
  value,
  onChange,
  rows = 8,
  placeholder,
}: {
  value: string;
  onChange: (v: string) => void;
  rows?: number;
  placeholder?: string;
}) {
  const [focused, setFocused] = useState(false);
  return (
    <textarea
      value={value}
      onChange={(e) => onChange(e.target.value)}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      rows={rows}
      placeholder={placeholder}
      style={{
        ...MONO,
        fontSize: 11.5,
        padding: "8px 12px",
        background: "#06060c",
        border: `1px solid ${focused ? "#00ff88" : "#1c1c28"}`,
        borderRadius: 4,
        color: "#c0ccd8",
        width: "100%",
        outline: "none",
        resize: "vertical",
        boxSizing: "border-box",
        boxShadow: focused ? "0 0 0 2px rgba(0,255,136,0.14)" : "none",
        transition: "border-color 0.15s, box-shadow 0.15s",
      }}
    />
  );
}

function ActionButton({
  onClick,
  color = "#00ff88",
  children,
  fullWidth,
  disabled,
}: {
  onClick: () => void;
  color?: string;
  children: React.ReactNode;
  fullWidth?: boolean;
  disabled?: boolean;
}) {
  const [hovered, setHovered] = useState(false);
  const bg = color === "#ff4455" ? "rgba(255,68,85,0.08)" : "rgba(0,255,136,0.08)";
  const bgHover = color === "#ff4455" ? "rgba(255,68,85,0.15)" : "rgba(0,255,136,0.15)";
  const border = color === "#ff4455" ? "rgba(255,68,85,0.3)" : "rgba(0,255,136,0.3)";
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        ...MONO,
        fontSize: 10,
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
        padding: "7px 14px",
        background: hovered ? bgHover : bg,
        border: `1px solid ${border}`,
        borderRadius: 4,
        color,
        cursor: disabled ? "not-allowed" : "pointer",
        opacity: disabled ? 0.5 : 1,
        width: fullWidth ? "100%" : undefined,
        transition: "background 0.15s",
      }}
    >
      {children}
    </button>
  );
}

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [selected, setSelected] = useState<string | null>(null);
  const [content, setContent] = useState("");
  const [loading, setLoading] = useState(true);
  const [creating, setCreating] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editContent, setEditContent] = useState("");
  const [saving, setSaving] = useState(false);
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
    setEditing(false);
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
        setNewName(""); setNewDesc(""); setNewContent("");
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Creation failed");
      }
    } catch {
      alert("Failed to create skill");
    }
  };

  const handleSave = async () => {
    if (!selected) return;
    setSaving(true);
    try {
      const res = await fetch("/api/skills", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name: selected, content: editContent }),
      });
      if (res.ok) {
        setContent(editContent);
        setEditing(false);
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Save failed");
      }
    } catch {
      alert("Failed to save skill");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete skill "${name}"?`)) return;
    try {
      const res = await fetch(`/api/skills?name=${encodeURIComponent(name)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        if (selected === name) { setSelected(null); setContent(""); setEditing(false); }
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Delete failed");
      }
    } catch {
      alert("Failed to delete skill");
    }
  };

  const startEdit = () => {
    setEditContent(content);
    setEditing(true);
  };

  const cancelEdit = () => {
    setEditing(false);
    setEditContent("");
  };

  const selectedSkill = skills.find((s) => s.name === selected);

  if (loading) {
    return (
      <div style={{ ...MONO, color: "#607888", fontSize: 13, padding: 40 }}>
        Loading skills…
      </div>
    );
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
      {/* Header */}
      <div>
        <div style={{ ...MONO, fontSize: 9, color: "#607888", letterSpacing: "0.2em", textTransform: "uppercase" }}>
          Claude Code
        </div>
        <h1 style={{ ...MONO, fontSize: 20, fontWeight: 700, color: "#00ff88", textShadow: "0 0 20px rgba(0,255,136,0.3)", marginTop: 2 }}>
          Skills
        </h1>
      </div>

      <div style={{ display: "flex", gap: 18, minHeight: "calc(100vh - 180px)" }}>
        {/* Left: Skill list */}
        <div style={{ ...PANEL, width: 300, flexShrink: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 0 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
            <div style={{ ...MONO, fontSize: 9, color: "#607888", letterSpacing: "0.16em", textTransform: "uppercase", fontWeight: 700 }}>
              Skills ({skills.length})
            </div>
            <ActionButton onClick={() => setCreating(!creating)} color={creating ? "#ff4455" : "#00ff88"}>
              {creating ? "✕ Cancel" : "+ New"}
            </ActionButton>
          </div>

          {creating && (
            <div style={{ ...PANEL, padding: 14, marginBottom: 14, background: "#06060c" }}>
              <div style={{ display: "flex", flexDirection: "column", gap: 8 }}>
                <div>
                  <div style={{ ...MONO, fontSize: 9, color: "#607888", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Name (slug)</div>
                  <TerminalInput value={newName} onChange={setNewName} placeholder="my-new-skill" />
                </div>
                <div>
                  <div style={{ ...MONO, fontSize: 9, color: "#607888", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Description</div>
                  <TerminalInput value={newDesc} onChange={setNewDesc} placeholder="Brief description" />
                </div>
                <div>
                  <div style={{ ...MONO, fontSize: 9, color: "#607888", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 4 }}>Content</div>
                  <TerminalTextarea value={newContent} onChange={setNewContent} rows={4} placeholder="# Skill content (markdown)" />
                </div>
                <ActionButton onClick={handleCreate} fullWidth>Create Skill</ActionButton>
              </div>
            </div>
          )}

          {skills.map((skill) => (
            <div
              key={skill.name}
              onClick={() => selectSkill(skill.name)}
              style={{
                padding: "10px 12px",
                marginBottom: 2,
                borderRadius: 4,
                cursor: "pointer",
                background: selected === skill.name ? "rgba(0,255,136,0.06)" : "transparent",
                borderLeft: selected === skill.name ? "2px solid #00ff88" : "2px solid transparent",
                transition: "background 0.15s",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ ...MONO, fontSize: 11, color: selected === skill.name ? "#00ff88" : "#c0ccd8", fontWeight: selected === skill.name ? 700 : 400 }}>
                  {skill.name}
                </span>
                <div style={{ display: "flex", gap: 6, alignItems: "center" }}>
                  {skill.is_core && (
                    <span style={{ ...MONO, fontSize: 8, color: "#607888", padding: "2px 5px", background: "#0a0a14", borderRadius: 3, border: "1px solid #1c1c28", textTransform: "uppercase", letterSpacing: "0.1em" }}>
                      core
                    </span>
                  )}
                  {!skill.is_core && (
                    <button
                      onClick={(e) => { e.stopPropagation(); handleDelete(skill.name); }}
                      style={{ ...MONO, padding: "2px 6px", fontSize: 9, background: "transparent", color: "#607888", border: "none", cursor: "pointer", transition: "color 0.15s" }}
                      onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#ff4455"; }}
                      onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.color = "#607888"; }}
                    >
                      ✕
                    </button>
                  )}
                </div>
              </div>
              <div style={{ ...MONO, fontSize: 10, color: "#9aa8b8", marginTop: 3, lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {skill.description}
              </div>
            </div>
          ))}
        </div>

        {/* Right: Skill content / editor */}
        <div style={{ ...PANEL, flex: 1, overflow: "auto", display: "flex", flexDirection: "column" }}>
          {selected ? (
            <>
              {/* Header bar */}
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, paddingBottom: 12, borderBottom: "1px solid #1c1c28" }}>
                <div>
                  <div style={{ ...MONO, fontSize: 14, fontWeight: 700, color: "#00ff88" }}>{selected}</div>
                  {selectedSkill?.description && (
                    <div style={{ ...MONO, fontSize: 10, color: "#9aa8b8", marginTop: 3 }}>{selectedSkill.description}</div>
                  )}
                </div>
                <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                  {selectedSkill?.last_modified && !editing && (
                    <span style={{ ...MONO, fontSize: 9, color: "#607888", letterSpacing: "0.08em" }}>
                      {new Date(selectedSkill.last_modified).toLocaleDateString()}
                    </span>
                  )}
                  {!editing && (
                    <ActionButton onClick={startEdit}>Edit</ActionButton>
                  )}
                  {editing && (
                    <>
                      <ActionButton onClick={handleSave} disabled={saving}>
                        {saving ? "Saving…" : "Save"}
                      </ActionButton>
                      <ActionButton onClick={cancelEdit} color="#ff4455">Cancel</ActionButton>
                    </>
                  )}
                </div>
              </div>

              {/* Content or editor */}
              {editing ? (
                <TerminalTextarea
                  value={editContent}
                  onChange={setEditContent}
                  rows={28}
                  placeholder="# Skill content (markdown)"
                />
              ) : (
                <div style={{
                  background: "#06060c",
                  padding: 16,
                  borderRadius: 6,
                  border: "1px solid #1c1c28",
                  flex: 1,
                  overflow: "auto",
                  color: "#a0b0c0",
                  lineHeight: 1.7,
                  fontSize: 13,
                }}>
                  <ReactMarkdown
                    components={{
                      h1: ({ children }) => (
                        <h1 style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 18, fontWeight: 700, color: "#00ff88", borderBottom: "1px solid #1c1c28", paddingBottom: 8, marginBottom: 14, marginTop: 0 }}>{children}</h1>
                      ),
                      h2: ({ children }) => (
                        <h2 style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 14, fontWeight: 700, color: "#c0e8ff", marginTop: 22, marginBottom: 8 }}>{children}</h2>
                      ),
                      h3: ({ children }) => (
                        <h3 style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 12, fontWeight: 700, color: "#9aa8b8", marginTop: 16, marginBottom: 6 }}>{children}</h3>
                      ),
                      p: ({ children }) => (
                        <p style={{ marginTop: 0, marginBottom: 10, color: "#a0b0c0" }}>{children}</p>
                      ),
                      ul: ({ children }) => (
                        <ul style={{ paddingLeft: 20, marginBottom: 10, color: "#a0b0c0" }}>{children}</ul>
                      ),
                      ol: ({ children }) => (
                        <ol style={{ paddingLeft: 20, marginBottom: 10, color: "#a0b0c0" }}>{children}</ol>
                      ),
                      li: ({ children }) => (
                        <li style={{ marginBottom: 4 }}>{children}</li>
                      ),
                      code: ({ children, className }) => {
                        const isBlock = className?.startsWith("language-");
                        return isBlock ? (
                          <pre style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, background: "#0a0a14", border: "1px solid #1c1c28", borderRadius: 4, padding: "10px 14px", overflowX: "auto", marginBottom: 12, color: "#c0e8ff" }}>
                            <code>{children}</code>
                          </pre>
                        ) : (
                          <code style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 11, background: "#0a0a14", border: "1px solid #1c1c28", borderRadius: 3, padding: "1px 5px", color: "#00ff88" }}>{children}</code>
                        );
                      },
                      blockquote: ({ children }) => (
                        <blockquote style={{ borderLeft: "3px solid #00ff88", paddingLeft: 12, marginLeft: 0, color: "#607888", fontStyle: "italic" }}>{children}</blockquote>
                      ),
                      a: ({ href, children }) => (
                        <a href={href} target="_blank" rel="noreferrer" style={{ color: "#00aaff", textDecoration: "none" }}>{children}</a>
                      ),
                      strong: ({ children }) => (
                        <strong style={{ color: "#c0e8ff", fontWeight: 700 }}>{children}</strong>
                      ),
                      em: ({ children }) => (
                        <em style={{ color: "#9aa8b8" }}>{children}</em>
                      ),
                      hr: () => (
                        <hr style={{ border: "none", borderTop: "1px solid #1c1c28", margin: "18px 0" }} />
                      ),
                      table: ({ children }) => (
                        <table style={{ width: "100%", borderCollapse: "collapse", marginBottom: 12, fontSize: 12 }}>{children}</table>
                      ),
                      th: ({ children }) => (
                        <th style={{ fontFamily: "'JetBrains Mono', monospace", textAlign: "left", padding: "5px 10px", borderBottom: "1px solid #1c1c28", color: "#607888", fontSize: 10, letterSpacing: "0.08em", textTransform: "uppercase" }}>{children}</th>
                      ),
                      td: ({ children }) => (
                        <td style={{ padding: "5px 10px", borderBottom: "1px solid #0d0d1a", color: "#a0b0c0" }}>{children}</td>
                      ),
                    }}
                  >
                    {content}
                  </ReactMarkdown>
                </div>
              )}
            </>
          ) : (
            <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: "100%", minHeight: 300 }}>
              <div style={{ textAlign: "center" }}>
                <div style={{ fontSize: 28, marginBottom: 10, opacity: 0.2 }}>◈</div>
                <div style={{ ...MONO, fontSize: 11, color: "#607888", letterSpacing: "0.12em", textTransform: "uppercase" }}>
                  Select a skill to view
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
