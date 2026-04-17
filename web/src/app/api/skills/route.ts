import { NextRequest, NextResponse } from "next/server";
import { apiError } from "@/lib/api-errors";
import fs from "fs/promises";
import path from "path";

// Skills are flat .md files, e.g. .claude/skills/trading-bot-overview.md
const SKILLS_DIR = process.env.SKILLS_DIR
  ? path.resolve(process.env.SKILLS_DIR)
  : path.resolve(process.cwd(), "..", ".claude", "skills");

const CORE_SKILLS = new Set([
  "trading-bot-overview",
  "coding-standards",
  "implement-agent",
  "add-strategy",
]);

function parseFrontmatter(text: string): Record<string, string> {
  const meta: Record<string, string> = {};
  if (!text.startsWith("---")) return meta;
  const end = text.indexOf("---", 3);
  if (end === -1) return meta;
  const block = text.slice(3, end).trim();
  for (const line of block.split("\n")) {
    const idx = line.indexOf(":");
    if (idx > 0) {
      meta[line.slice(0, idx).trim()] = line
        .slice(idx + 1)
        .trim()
        .replace(/^"(.*)"$/, "$1"); // strip surrounding quotes
    }
  }
  return meta;
}

/** Resolve the file path for a skill by slug.
 *  Checks flat <slug>.md first, then directory <slug>/index.md. */
async function resolveSkillFile(slug: string): Promise<string | null> {
  const flat = path.join(SKILLS_DIR, `${slug}.md`);
  try { await fs.access(flat); return flat; } catch { /* fall through */ }
  const nested = path.join(SKILLS_DIR, slug, "index.md");
  try { await fs.access(nested); return nested; } catch { /* fall through */ }
  return null;
}

// GET /api/skills        → list all skills
// GET /api/skills?name=  → read one skill
export async function GET(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const name = searchParams.get("name");

  if (name) {
    const filePath = await resolveSkillFile(name);
    if (!filePath) return apiError("NOT_FOUND", `Skill '${name}' not found`, 404);
    try {
      const content = await fs.readFile(filePath, "utf-8");
      const meta = parseFrontmatter(content);
      return NextResponse.json({ name, content, ...meta });
    } catch {
      return apiError("NOT_FOUND", `Skill '${name}' not found`, 404);
    }
  }

  // List all skills — collect both flat .md files and directory/index.md
  try {
    const entries = await fs.readdir(SKILLS_DIR, { withFileTypes: true });
    const skills = [];
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      let slug: string;
      let filePath: string;

      if (entry.isFile() && entry.name.endsWith(".md")) {
        slug = entry.name.slice(0, -3);
        filePath = path.join(SKILLS_DIR, entry.name);
      } else if (entry.isDirectory()) {
        slug = entry.name;
        filePath = path.join(SKILLS_DIR, entry.name, "index.md");
        try { await fs.access(filePath); } catch { continue; }
      } else {
        continue;
      }

      try {
        const content = await fs.readFile(filePath, "utf-8");
        const meta = parseFrontmatter(content);
        const stat = await fs.stat(filePath);
        skills.push({
          name: meta.name || slug,
          description: meta.description || "",
          location: filePath,
          user_invocable: (meta["user-invocable"] || "true").toLowerCase() !== "false",
          is_core: CORE_SKILLS.has(slug),
          last_modified: stat.mtime.toISOString(),
        });
      } catch {
        // skip unreadable files
      }
    }
    return NextResponse.json({ skills });
  } catch {
    return NextResponse.json({ skills: [] });
  }
}

// POST /api/skills  → create a new skill
export async function POST(request: NextRequest) {
  const body = await request.json();
  const { name, description, content } = body;
  if (!name || !description || !content) {
    return apiError("VALIDATION_ERROR", "name, description, and content are required", 400);
  }
  if (!/^[a-z][a-z0-9-]*$/.test(name)) {
    return apiError("VALIDATION_ERROR", "Name must be lowercase with hyphens only", 400);
  }

  const existing = await resolveSkillFile(name);
  if (existing) {
    return apiError("CONFLICT", `Skill '${name}' already exists`, 409);
  }

  // New skills always created as flat .md files
  const filePath = path.join(SKILLS_DIR, `${name}.md`);
  const md = `---\nname: ${name}\ndescription: "${description}"\n---\n\n${content}\n`;
  await fs.writeFile(filePath, md, "utf-8");

  return NextResponse.json({ ok: true, name });
}

// PUT /api/skills  → update an existing skill
export async function PUT(request: NextRequest) {
  const body = await request.json();
  const { name, content, description } = body;
  if (!name || !content) {
    return apiError("VALIDATION_ERROR", "name and content are required", 400);
  }

  const filePath = await resolveSkillFile(name);
  if (!filePath) return apiError("NOT_FOUND", `Skill '${name}' not found`, 404);
  let existing = "";
  try {
    existing = await fs.readFile(filePath, "utf-8");
  } catch {
    return apiError("NOT_FOUND", `Skill '${name}' not found`, 404);
  }

  let finalContent = content;
  if (description !== undefined) {
    const meta = parseFrontmatter(existing);
    const updatedMeta = { ...meta, description };
    const bodyStart = content.startsWith("---") ? content.indexOf("---", 3) + 3 : -1;
    const bodyText = bodyStart > 0 ? content.slice(bodyStart).trim() : content;
    const fmLines = Object.entries(updatedMeta)
      .map(([k, v]) => `${k}: ${v}`)
      .join("\n");
    finalContent = `---\n${fmLines}\n---\n\n${bodyText}\n`;
  }

  await fs.writeFile(filePath, finalContent, "utf-8");
  const stat = await fs.stat(filePath);
  return NextResponse.json({ ok: true, name, last_modified: stat.mtime.toISOString() });
}

// DELETE /api/skills?name=  → delete a skill
export async function DELETE(request: NextRequest) {
  const searchParams = request.nextUrl.searchParams;
  const name = searchParams.get("name");
  if (!name) {
    return apiError("VALIDATION_ERROR", "name query parameter required", 400);
  }
  if (CORE_SKILLS.has(name)) {
    return apiError("FORBIDDEN", `Cannot delete core skill '${name}'`, 403);
  }

  const resolved = await resolveSkillFile(name);
  if (!resolved) return apiError("NOT_FOUND", `Skill '${name}' not found`, 404);
  try {
    if (resolved.endsWith("index.md")) {
      await fs.rm(path.dirname(resolved), { recursive: true });
    } else {
      await fs.unlink(resolved);
    }
    return NextResponse.json({ ok: true, name });
  } catch {
    return apiError("NOT_FOUND", `Skill '${name}' not found`, 404);
  }
}
