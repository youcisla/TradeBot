import { NextResponse } from "next/server";
import { getAllTrades } from "@/lib/db";

export const dynamic = "force-dynamic";

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url);
  const symbol = searchParams.get("symbol");

  try {
    const allTrades = await getAllTrades(500);

    const trades = symbol
      ? allTrades.filter((t) => t.symbol === symbol)
      : allTrades;

    // Build markers (entry/exit points) and price lines (SL/TP levels)
    const markers = trades.map((t) => {
      const items: Array<{
        time: number;
        position: string;
        color: string;
        shape: string;
        text: string;
        type: string;
      }> = [];

      // Entry marker
      if (t.open_time) {
        items.push({
          time: Math.floor(new Date(t.open_time).getTime() / 1000),
          position: t.direction === "BUY" ? "belowBar" : "aboveBar",
          color: t.direction === "BUY" ? "#00ff88" : "#ff4444",
          shape: t.direction === "BUY" ? "arrowUp" : "arrowDown",
          text: `${t.direction} ${Number(t.entry_price).toFixed(5)}`,
          type: "entry",
        });
      }

      // Exit marker
      if (t.close_time && t.status === "CLOSED") {
        items.push({
          time: Math.floor(new Date(t.close_time).getTime() / 1000),
          position: t.direction === "BUY" ? "aboveBar" : "belowBar",
          color: Number(t.pnl) >= 0 ? "#00ff88" : "#ff4444",
          shape: "circle",
          text: `${t.close_reason || "CLOSE"} ${Number(t.pnl) >= 0 ? "+" : ""}${Number(t.pnl).toFixed(2)}`,
          type: "exit",
        });
      }

      return items;
    }).flat();

    // Price lines for open trades (SL/TP)
    const priceLines = trades
      .filter((t) => t.status === "OPEN" || t.status === "PARTIAL")
      .map((t) => {
        const lines: Array<{
          price: number;
          color: string;
          lineWidth: number;
          lineStyle: number;
          title: string;
        }> = [];

        if (Number(t.stop_loss)) {
          lines.push({
            price: Number(t.stop_loss),
            color: "#ff4444",
            lineWidth: 1,
            lineStyle: 2, // dashed
            title: "SL",
          });
        }
        if (Number(t.take_profit_1)) {
          lines.push({
            price: Number(t.take_profit_1),
            color: "#00ff88",
            lineWidth: 1,
            lineStyle: 2,
            title: "TP1",
          });
        }
        if (Number(t.take_profit_2)) {
          lines.push({
            price: Number(t.take_profit_2),
            color: "#00cc33",
            lineWidth: 1,
            lineStyle: 2,
            title: "TP2",
          });
        }
        if (Number(t.take_profit_3)) {
          lines.push({
            price: Number(t.take_profit_3),
            color: "#009922",
            lineWidth: 1,
            lineStyle: 2,
            title: "TP3",
          });
        }
        if (Number(t.entry_price)) {
          lines.push({
            price: Number(t.entry_price),
            color: "#eab308",
            lineWidth: 1,
            lineStyle: 0, // solid
            title: `Entry ${t.direction}`,
          });
        }

        return lines;
      })
      .flat();

    return NextResponse.json({ markers, priceLines });
  } catch (err) {
    console.error("[api/candles/trades]", (err as Error).message);
    return NextResponse.json(
      { error: "DB temporarily unavailable" },
      { status: 503 }
    );
  }
}
