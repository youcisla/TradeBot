import { NextRequest, NextResponse } from "next/server";
import { pool } from "@/lib/db";

export const dynamic = "force-dynamic";

const SANE_LIMIT = 500;

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ table: string }> }
) {
  const { table: rawTable } = await params;
  const table = rawTable.replace(/[^a-z0-9_]/gi, "");
  if (!table) return NextResponse.json({ error: "Invalid table" }, { status: 400 });

  const searchParams = await req.nextUrl.searchParams;
  const page = Math.max(1, parseInt(searchParams.get("page") ?? "1", 10));
  const pageSize = Math.min(SANE_LIMIT, Math.max(1, parseInt(searchParams.get("pageSize") ?? "25", 10)));
  const search = searchParams.get("search") ?? "";
  const sortBy = searchParams.get("sortBy") ?? "";
  const sortDir = searchParams.get("sortDir") === "desc" ? "DESC" : "ASC";

  const offset = (page - 1) * pageSize;

  try {
    const client = await pool.connect();
    try {
      // Build WHERE clause for search
      let whereClause = "";
      let queryArgs: (string | number)[] = [];

      if (search) {
        const colResult = await client.query(
          `SELECT column_name FROM information_schema.columns
           WHERE table_schema = 'public' AND table_name = $1 AND data_type IN ('text','varchar','character varying')
           LIMIT 20`,
          [table]
        );
        const textCols = colResult.rows.map((r) => r.column_name);
        if (textCols.length > 0) {
          const searchConditions = textCols.map((c) => `CAST("${c}" AS TEXT) ILIKE $2`);
          whereClause = "WHERE " + searchConditions.join(" OR ");
          queryArgs = [table, `%${search}%`];
        }
      } else {
        queryArgs = [table];
      }

      // Get total count
      const countRes = await client.query(
        `SELECT COUNT(*) FROM "${table}"${whereClause ? " " + whereClause : ""}`,
        queryArgs
      );
      const total = parseInt(countRes.rows[0].count, 10);

      // Get rows with optional sort
      let orderClause = "";
      if (sortBy) {
        const safeCol = sortBy.replace(/[^a-z0-9_]/gi, "");
        if (safeCol) orderClause = ` ORDER BY "${safeCol}" ${sortDir}`;
      }

      const rowsRes = await client.query(
        `SELECT * FROM "${table}"${whereClause ? " " + whereClause : ""}${orderClause} LIMIT $${queryArgs.length + 1} OFFSET $${queryArgs.length + 2}`,
        [...queryArgs, pageSize, offset]
      );

      // Get schema
      const schemaRes = await client.query(
        `SELECT column_name, data_type, is_nullable
         FROM information_schema.columns
         WHERE table_schema = 'public' AND table_name = $1
         ORDER BY ordinal_position`,
        [table]
      );

      return NextResponse.json({
        rows: rowsRes.rows,
        total,
        page,
        pageSize,
        schema: schemaRes.rows,
      });
    } finally {
      client.release();
    }
  } catch (err) {
    return NextResponse.json({ error: String(err) }, { status: 500 });
  }
}