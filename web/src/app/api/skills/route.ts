import { NextResponse } from "next/server";
import { getServerSession } from "next-auth";
import { authOptions } from "@/lib/auth";
import fs from "fs/promises";
import path from "path";

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
      meta[line.slice(0, idx).trim()] = line.slice(idx + 1).trim();
    }
  }
  return meta;
}

// GET /api/skills  → list all skills
// GET /api/skills?name=<skill>  → read a skill
export async function GET(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const name = searchParams.get("name");

  if (name) {
    // Read single skill
    const skillFile = path.join(SKILLS_DIR, name, "SKILL.md");
    try {
      const content = await fs.readFile(skillFile, "utf-8");
      const meta = parseFrontmatter(content);
      return NextResponse.json({ name, content, ...meta });
    } catch {
      return NextResponse.json({ error: `Skill '${name}' not found` }, { status: 404 });
    }
  }

  // List all skills
  try {
    const entries = await fs.readdir(SKILLS_DIR, { withFileTypes: true });
    const skills = [];
    for (const entry of entries.sort((a, b) => a.name.localeCompare(b.name))) {
      if (!entry.isDirectory()) continue;
      const skillFile = path.join(SKILLS_DIR, entry.name, "SKILL.md");
      try {
        const content = await fs.readFile(skillFile, "utf-8");
        const meta = parseFrontmatter(content);
        const stat = await fs.stat(skillFile);
        skills.push({
          name: meta.name || entry.name,
          description: meta.description || "",
          location: skillFile,
          user_invocable: (meta["user-invocable"] || "true").toLowerCase() !== "false",
          is_core: CORE_SKILLS.has(entry.name),
          last_modified: stat.mtime.toISOString(),
        });
      } catch {
        // skip directories without SKILL.md
      }
    }
    return NextResponse.json({ skills });
  } catch {
    return NextResponse.json({ skills: [] });
  }
}

// POST /api/skills  → create a new skill
export async function POST(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { name, description, content } = body;
  if (!name || !description || !content) {
    return NextResponse.json({ error: "name, description, and content are required" }, { status: 400 });
  }
  if (!/^[a-z][a-z0-9-]*$/.test(name)) {
    return NextResponse.json({ error: "Name must be lowercase with hyphens only" }, { status: 400 });
  }

  const skillDir = path.join(SKILLS_DIR, name);
  try {
    await fs.access(skillDir);
    return NextResponse.json({ error: `Skill '${name}' already exists` }, { status: 409 });
  } catch {
    // does not exist — good
  }

  const md = `---\nname: ${name}\ndescription: ${description}\n---\n\n${content}\n`;
  await fs.mkdir(skillDir, { recursive: true });
  await fs.writeFile(path.join(skillDir, "SKILL.md"), md, "utf-8");

  return NextResponse.json({ ok: true, name });
}

// PUT /api/skills  → update an existing skill's content and/or description
export async function PUT(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const body = await request.json();
  const { name, content, description } = body;
  if (!name || !content) {
    return NextResponse.json({ error: "name and content are required" }, { status: 400 });
  }

  const skillFile = path.join(SKILLS_DIR, name, "SKILL.md");
  let existing = "";
  try {
    existing = await fs.readFile(skillFile, "utf-8");
  } catch {
    return NextResponse.json({ error: `Skill '${name}' not found` }, { status: 404 });
  }

  // If description supplied, update the frontmatter; otherwise preserve it
  let finalContent = content;
  if (description !== undefined) {
    const meta = parseFrontmatter(existing);
    const updatedMeta = { ...meta, description };
    // Strip body from content (in case caller sent full SKILL.md with frontmatter)
    const bodyStart = content.startsWith("---")
      ? content.indexOf("---", 3) + 3
      : -1;
    const bodyText = bodyStart > 0 ? content.slice(bodyStart).trim() : content;
    const fmLines = Object.entries(updatedMeta)
      .map(([k, v]) => `${k}: ${v}`)
      .join("\n");
    finalContent = `---\n${fmLines}\n---\n\n${bodyText}\n`;
  }

  await fs.writeFile(skillFile, finalContent, "utf-8");

  // Return last_modified so the UI can display it
  const stat = await fs.stat(skillFile);
  return NextResponse.json({ ok: true, name, last_modified: stat.mtime.toISOString() });
}

// DELETE /api/skills?name=<skill>  → delete a skill
export async function DELETE(request: Request) {
  const session = await getServerSession(authOptions);
  if (!session) return NextResponse.json({ error: "Unauthorized" }, { status: 401 });

  const { searchParams } = new URL(request.url);
  const name = searchParams.get("name");
  if (!name) {
    return NextResponse.json({ error: "name query parameter required" }, { status: 400 });
  }
  if (CORE_SKILLS.has(name)) {
    return NextResponse.json({ error: `Cannot delete core skill '${name}'` }, { status: 403 });
  }

  const skillDir = path.join(SKILLS_DIR, name);
  try {
    await fs.rm(skillDir, { recursive: true });
    return NextResponse.json({ ok: true, name });
  } catch {
    return NextResponse.json({ error: `Skill '${name}' not found` }, { status: 404 });
  }
}
