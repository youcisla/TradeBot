"use client";

import { useEffect, useState, useCallback } from "react";
import ReactMarkdown from "react-markdown";

// ── Types ─────────────────────────────────────────────────────────────────────

interface Skill {
  name: string;
  description: string;
  location: string;
  user_invocable: boolean;
  is_core: boolean;
  last_modified?: string;
}

// ── Design tokens ─────────────────────────────────────────────────────────────

const SF: React.CSSProperties = {
  fontFamily: `-apple-system, BlinkMacSystemFont, "SF Pro Display", system-ui, sans-serif`,
};

const MONO: React.CSSProperties = {
  fontFamily: `"SF Mono", SFMono-Regular, ui-monospace, Menlo, monospace`,
};

// ── Sub-components ────────────────────────────────────────────────────────────

function SearchBar({ value, onChange }: { value: string; onChange: (v: string) => void }) {
  const [focused, setFocused] = useState(false);
  return (
    <div style={{ position: "relative", marginBottom: 12 }}>
      <span style={{
        position: "absolute",
        left: 12,
        top: "50%",
        transform: "translateY(-50%)",
        color: "rgba(235,235,245,0.4)",
        fontSize: 16,
        pointerEvents: "none",
      }}>
        ⌕
      </span>
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="Search skills…"
        style={{
          ...SF,
          width: "100%",
          height: 36,
          background: "rgba(120,120,128,0.24)",
          border: `1px solid ${focused ? "#0A84FF" : "transparent"}`,
          borderRadius: 10,
          padding: "0 12px 0 34px",
          fontSize: 15,
          color: "#FFFFFF",
          outline: "none",
          boxSizing: "border-box",
          boxShadow: focused ? "0 0 0 3px rgba(10,132,255,0.2)" : "none",
          transition: "border-color 0.15s, box-shadow 0.15s",
        }}
      />
    </div>
  );
}

function TypeBadge({ isCore, userInvocable }: { isCore: boolean; userInvocable: boolean }) {
  if (isCore) return (
    <span style={{
      ...SF,
      fontSize: 11,
      fontWeight: 600,
      background: "rgba(100,210,255,0.15)",
      color: "#64D2FF",
      border: "1px solid rgba(100,210,255,0.3)",
      borderRadius: 4,
      padding: "2px 7px",
      whiteSpace: "nowrap",
    }}>
      Project
    </span>
  );
  if (userInvocable) return (
    <span style={{
      ...SF,
      fontSize: 11,
      fontWeight: 600,
      background: "rgba(191,90,242,0.15)",
      color: "#BF5AF2",
      border: "1px solid rgba(191,90,242,0.3)",
      borderRadius: 4,
      padding: "2px 7px",
      whiteSpace: "nowrap",
    }}>
      Global
    </span>
  );
  return (
    <span style={{
      ...SF,
      fontSize: 11,
      fontWeight: 600,
      background: "rgba(142,142,147,0.15)",
      color: "#8E8E93",
      border: "1px solid rgba(142,142,147,0.3)",
      borderRadius: 4,
      padding: "2px 7px",
      whiteSpace: "nowrap",
    }}>
      Skill
    </span>
  );
}

function SkillRow({
  skill,
  expanded,
  selected,
  expandedContent,
  onClick,
  onDelete,
  last,
}: {
  skill: Skill;
  expanded: boolean;
  selected: boolean;
  expandedContent: string;
  onClick: () => void;
  onDelete: (name: string) => void;
  last: boolean;
}) {
  return (
    <>
      <div
        onClick={onClick}
        style={{
          display: "flex",
          alignItems: "center",
          minHeight: 52,
          padding: "10px 16px",
          cursor: "pointer",
          gap: 12,
          background: selected ? "rgba(10,132,255,0.08)" : "transparent",
          transition: "background 0.1s",
        }}
        onMouseEnter={(e) => {
          if (!selected) (e.currentTarget as HTMLDivElement).style.background = "rgba(120,120,128,0.12)";
        }}
        onMouseLeave={(e) => {
          if (!selected) (e.currentTarget as HTMLDivElement).style.background = "transparent";
        }}
      >
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 3 }}>
            <span style={{
              ...SF,
              fontSize: 15,
              fontWeight: 600,
              color: selected ? "#0A84FF" : "#FFFFFF",
            }}>
              {skill.name}
            </span>
            <TypeBadge isCore={skill.is_core} userInvocable={skill.user_invocable} />
          </div>
          <div style={{
            ...SF,
            fontSize: 13,
            color: "rgba(235,235,245,0.4)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}>
            {skill.description || "No description"}
          </div>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8, flexShrink: 0 }}>
          {!skill.is_core && (
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(skill.name); }}
              style={{
                width: 28,
                height: 28,
                borderRadius: "50%",
                background: "rgba(255,69,58,0.1)",
                border: "1px solid rgba(255,69,58,0.25)",
                color: "#FF453A",
                fontSize: 14,
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                flexShrink: 0,
                transition: "background 0.12s",
              }}
              onMouseEnter={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,69,58,0.2)";
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,69,58,0.1)";
              }}
            >
              ×
            </button>
          )}
          <svg
            width="8" height="13" viewBox="0 0 8 13" fill="none"
            style={{
              opacity: 0.3,
              transform: expanded ? "rotate(90deg)" : "none",
              transition: "transform 0.2s",
            }}
          >
            <path d="M1 1l6 5.5L1 12" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        </div>
      </div>

      {/* Expanded content */}
      {expanded && expandedContent && (
        <div style={{
          background: "#2C2C2E",
          margin: "0 12px 12px",
          borderRadius: 10,
          padding: "14px 16px",
          fontSize: 13,
          color: "rgba(235,235,245,0.7)",
          lineHeight: 1.6,
          maxHeight: 300,
          overflowY: "auto",
        }}>
          <ReactMarkdown
            components={{
              h1: ({ children }) => <h1 style={{ ...SF, fontSize: 15, fontWeight: 700, color: "#FFFFFF", marginTop: 0, marginBottom: 10 }}>{children}</h1>,
              h2: ({ children }) => <h2 style={{ ...SF, fontSize: 14, fontWeight: 600, color: "#64D2FF", marginTop: 14, marginBottom: 8 }}>{children}</h2>,
              h3: ({ children }) => <h3 style={{ ...SF, fontSize: 13, fontWeight: 600, color: "rgba(235,235,245,0.7)", marginTop: 10, marginBottom: 6 }}>{children}</h3>,
              p: ({ children }) => <p style={{ marginTop: 0, marginBottom: 8 }}>{children}</p>,
              ul: ({ children }) => <ul style={{ paddingLeft: 18, marginBottom: 8 }}>{children}</ul>,
              ol: ({ children }) => <ol style={{ paddingLeft: 18, marginBottom: 8 }}>{children}</ol>,
              li: ({ children }) => <li style={{ marginBottom: 3 }}>{children}</li>,
              code: ({ children, className }) => {
                const isBlock = className?.startsWith("language-");
                return isBlock ? (
                  <pre style={{ ...MONO, fontSize: 11, background: "#1C1C1E", borderRadius: 8, padding: "10px 12px", overflowX: "auto", marginBottom: 10, color: "#64D2FF" }}>
                    <code>{children}</code>
                  </pre>
                ) : (
                  <code style={{ ...MONO, fontSize: 11, background: "#1C1C1E", borderRadius: 4, padding: "1px 5px", color: "#30D158" }}>{children}</code>
                );
              },
              strong: ({ children }) => <strong style={{ color: "#FFFFFF", fontWeight: 600 }}>{children}</strong>,
              a: ({ href, children }) => <a href={href} target="_blank" rel="noreferrer" style={{ color: "#0A84FF", textDecoration: "none" }}>{children}</a>,
            }}
          >
            {expandedContent}
          </ReactMarkdown>
        </div>
      )}

      {!last && (
        <div style={{ height: "0.5px", background: "rgba(84,84,88,0.65)", marginLeft: 16 }} />
      )}
    </>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function SkillsPage() {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);
  const [expandedContent, setExpandedContent] = useState<Record<string, string>>({});
  const [creating, setCreating] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [newContent, setNewContent] = useState("");
  const [createFocused, setCreateFocused] = useState<string | null>(null);

  const fetchSkills = useCallback(async () => {
    try {
      const res = await fetch("/api/skills");
      const data = await res.json();
      setSkills(data.skills || []);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchSkills(); }, [fetchSkills]);

  const handleSelect = async (name: string) => {
    if (selected === name) { setSelected(null); return; }
    setSelected(name);
    if (!expandedContent[name]) {
      try {
        const res = await fetch(`/api/skills?name=${encodeURIComponent(name)}`);
        const data = await res.json();
        setExpandedContent((prev) => ({ ...prev, [name]: data.content || "" }));
      } catch {
        setExpandedContent((prev) => ({ ...prev, [name]: "Failed to load content." }));
      }
    }
  };

  const handleDelete = async (name: string) => {
    if (!confirm(`Delete skill "${name}"?`)) return;
    try {
      const res = await fetch(`/api/skills?name=${encodeURIComponent(name)}`, { method: "DELETE" });
      if (res.ok) {
        if (selected === name) setSelected(null);
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Delete failed");
      }
    } catch { alert("Failed to delete skill"); }
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
        setCreating(false); setNewName(""); setNewDesc(""); setNewContent("");
        await fetchSkills();
      } else {
        const data = await res.json();
        alert(data.error || "Creation failed");
      }
    } catch { alert("Failed to create skill"); }
  };

  // Filter & group
  const filtered = search
    ? skills.filter((s) => s.name.toLowerCase().includes(search.toLowerCase()) || s.description.toLowerCase().includes(search.toLowerCase()))
    : skills;

  const projectSkills = filtered.filter((s) => s.is_core);
  const globalSkills = filtered.filter((s) => !s.is_core);

  if (loading) {
    return (
      <div style={{
        ...SF,
        paddingTop: 20,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        height: 300,
        gap: 12,
      }}>
        <div style={{
          width: 28,
          height: 28,
          border: "2px solid rgba(84,84,88,0.4)",
          borderTop: "2px solid #0A84FF",
          borderRadius: "50%",
          animation: "spin 0.8s linear infinite",
        }} />
        <span style={{ fontSize: 15, color: "rgba(235,235,245,0.4)" }}>Loading skills…</span>
        <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
      </div>
    );
  }

  const inputStyle = (field: string): React.CSSProperties => ({
    ...SF,
    width: "100%",
    background: "rgba(120,120,128,0.24)",
    border: `1px solid ${createFocused === field ? "#0A84FF" : "transparent"}`,
    borderRadius: 10,
    padding: "10px 12px",
    fontSize: 15,
    color: "#FFFFFF",
    outline: "none",
    boxSizing: "border-box",
    boxShadow: createFocused === field ? "0 0 0 3px rgba(10,132,255,0.2)" : "none",
    transition: "border-color 0.15s, box-shadow 0.15s",
    resize: "vertical" as const,
  });

  return (
    <div style={{ ...SF, paddingTop: 20, paddingBottom: 40 }}>
      {/* Header */}
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: 20 }}>
        <h1 style={{
          fontSize: 34,
          fontWeight: 700,
          color: "#FFFFFF",
          margin: 0,
          letterSpacing: "-0.02em",
        }}>
          Skill Lab
        </h1>
        <button
          onClick={() => setCreating(!creating)}
          style={{
            width: 36,
            height: 36,
            borderRadius: "50%",
            background: creating ? "rgba(255,69,58,0.15)" : "rgba(10,132,255,0.15)",
            border: `1px solid ${creating ? "rgba(255,69,58,0.4)" : "rgba(10,132,255,0.4)"}`,
            color: creating ? "#FF453A" : "#0A84FF",
            fontSize: 22,
            fontWeight: 300,
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            transition: "background 0.15s",
            lineHeight: 1,
          }}
        >
          {creating ? "×" : "+"}
        </button>
      </div>

      {/* Search */}
      <SearchBar value={search} onChange={setSearch} />

      {/* Create form */}
      {creating && (
        <div style={{
          background: "#1C1C1E",
          borderRadius: 12,
          padding: "20px 16px",
          marginBottom: 24,
        }}>
          <div style={{ fontSize: 17, fontWeight: 600, color: "#FFFFFF", marginBottom: 16 }}>New Skill</div>
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            <div>
              <div style={{ fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>Slug name</div>
              <input
                value={newName}
                onChange={(e) => setNewName(e.target.value)}
                onFocus={() => setCreateFocused("name")}
                onBlur={() => setCreateFocused(null)}
                placeholder="my-new-skill"
                style={inputStyle("name")}
              />
            </div>
            <div>
              <div style={{ fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>Description</div>
              <input
                value={newDesc}
                onChange={(e) => setNewDesc(e.target.value)}
                onFocus={() => setCreateFocused("desc")}
                onBlur={() => setCreateFocused(null)}
                placeholder="Brief description of what this skill does"
                style={inputStyle("desc")}
              />
            </div>
            <div>
              <div style={{ fontSize: 13, color: "rgba(235,235,245,0.6)", marginBottom: 6 }}>Content (Markdown)</div>
              <textarea
                value={newContent}
                onChange={(e) => setNewContent(e.target.value)}
                onFocus={() => setCreateFocused("content")}
                onBlur={() => setCreateFocused(null)}
                rows={6}
                placeholder="# Skill title&#10;Describe what Claude should do..."
                style={{ ...inputStyle("content"), ...MONO, fontSize: 13 }}
              />
            </div>
            <div style={{ display: "flex", gap: 10 }}>
              <button
                onClick={handleCreate}
                disabled={!newName || !newDesc || !newContent}
                style={{
                  ...SF,
                  flex: 1,
                  height: 44,
                  background: "#0A84FF",
                  border: "none",
                  borderRadius: 12,
                  fontSize: 17,
                  fontWeight: 600,
                  color: "#FFFFFF",
                  cursor: (!newName || !newDesc || !newContent) ? "not-allowed" : "pointer",
                  opacity: (!newName || !newDesc || !newContent) ? 0.5 : 1,
                }}
              >
                Create Skill
              </button>
              <button
                onClick={() => setCreating(false)}
                style={{
                  ...SF,
                  flex: 1,
                  height: 44,
                  background: "rgba(120,120,128,0.24)",
                  border: "none",
                  borderRadius: 12,
                  fontSize: 17,
                  fontWeight: 600,
                  color: "#FFFFFF",
                  cursor: "pointer",
                }}
              >
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Project skills group */}
      {projectSkills.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            fontSize: 13,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            marginBottom: 8,
            paddingLeft: 4,
          }}>
            Project Skills ({projectSkills.length})
          </div>
          <div style={{ background: "#1C1C1E", borderRadius: 12, overflow: "hidden" }}>
            {projectSkills.map((skill, i) => (
              <SkillRow
                key={skill.name}
                skill={skill}
                expanded={selected === skill.name}
                selected={selected === skill.name}
                expandedContent={expandedContent[skill.name] || ""}
                onClick={() => handleSelect(skill.name)}
                onDelete={handleDelete}
                last={i === projectSkills.length - 1}
              />
            ))}
          </div>
        </div>
      )}

      {/* Global skills group */}
      {globalSkills.length > 0 && (
        <div style={{ marginBottom: 24 }}>
          <div style={{
            fontSize: 13,
            color: "rgba(235,235,245,0.6)",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            marginBottom: 8,
            paddingLeft: 4,
          }}>
            Global Skills ({globalSkills.length})
          </div>
          <div style={{ background: "#1C1C1E", borderRadius: 12, overflow: "hidden" }}>
            {globalSkills.map((skill, i) => (
              <SkillRow
                key={skill.name}
                skill={skill}
                expanded={selected === skill.name}
                selected={selected === skill.name}
                expandedContent={expandedContent[skill.name] || ""}
                onClick={() => handleSelect(skill.name)}
                onDelete={handleDelete}
                last={i === globalSkills.length - 1}
              />
            ))}
          </div>
        </div>
      )}

      {filtered.length === 0 && !loading && (
        <div style={{
          textAlign: "center",
          padding: "60px 20px",
          color: "rgba(235,235,245,0.3)",
          fontSize: 15,
        }}>
          No skills found{search ? ` for "${search}"` : ""}
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
