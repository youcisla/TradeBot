import { NextResponse } from "next/server";
import { readFile } from "fs/promises";
import { join } from "path";

export const dynamic = "force-dynamic";

export async function GET() {
  try {
    // Symbols manifest written by Python bot at startup
    const filePath = join(process.cwd(), "..", "data", "symbols.json");
    let payload = "{}";
    try {
      payload = await readFile(filePath, "utf-8");
    } catch {
      // Bot hasn't written the manifest yet (first startup)
    }
    const data = JSON.parse(payload);
    return NextResponse.json(data, {
      headers: { "Cache-Control": "no-store" },
    });
  } catch (err) {
    console.error("[api/symbols] error:", err);
    return NextResponse.json(
      { error: { code: "INTERNAL_ERROR", message: "Failed to load symbols" } },
      { status: 500 }
    );
  }
}
