"use client";

import { useEffect, useRef, useCallback, useState } from "react";
import {
  createChart,
  type IChartApi,
  type ISeriesApi,
  type CandlestickData,
  type HistogramData,
  type Time,
  ColorType,
  LineStyle,
  CrosshairMode,
} from "lightweight-charts";

interface CandleRaw {
  time: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
}

interface TradeMarker {
  time: number;
  position: string;
  color: string;
  shape: string;
  text: string;
  type: string;
}

interface PriceLine {
  price: number;
  color: string;
  lineWidth: number;
  lineStyle: number;
  title: string;
}

interface FibLevel {
  ratio: number;
  price: number;
  label: string;
}

interface FibData {
  direction: string;
  anchor_low: number;
  anchor_high: number;
  levels: FibLevel[];
  golden_zone: { top: number; bottom: number } | null;
  confluence: {
    gz_fvg: boolean;
    gz_ob: boolean;
    gz_ce: boolean;
    has_target: boolean;
  };
  retracement_depth: string;
}

interface Props {
  symbol: string;
  timeframe: string;
  count?: number;
}

export default function TradingChart({ symbol, timeframe, count = 500 }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const volumeSeriesRef = useRef<ISeriesApi<"Histogram"> | null>(null);
  const lastTimeRef = useRef<number>(0);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "error">("loading");
  const statusRef = useRef<"loading" | "ok" | "error">("loading");
  const errorReasonRef = useRef<"server_down" | "no_data">("server_down");
  // Stop polling once server is confirmed down — prevents console spam from repeated 503s
  const serverDownRef = useRef(false);
  const setStatusSync = (s: "loading" | "ok" | "error") => {
    statusRef.current = s;
    setStatus(s);
  };

  const fetchCandles = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&count=${count}`
      );
      if (!res.ok) {
        if (res.status === 503) serverDownRef.current = true;
        return null;
      }
      return (await res.json()) as CandleRaw[];
    } catch {
      serverDownRef.current = true;
      return null;
    }
  }, [symbol, timeframe, count]);

  const fetchOverlays = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/candles/trades?symbol=${encodeURIComponent(symbol)}`
      );
      if (!res.ok) return null;
      return (await res.json()) as {
        markers: TradeMarker[];
        priceLines: PriceLine[];
      };
    } catch {
      return null;
    }
  }, [symbol]);

  const fetchFibonacci = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/candles/fibonacci?symbol=${encodeURIComponent(symbol)}`
      );
      if (!res.ok) return null;
      const data = await res.json();
      if (!data.levels || data.levels.length === 0) return null;
      return data as FibData;
    } catch {
      return null;
    }
  }, [symbol]);

  // Initialize chart
  useEffect(() => {
    if (!containerRef.current) return;

    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0D0D0F" },
        textColor: "#8A8A93",
        fontFamily: "'IBM Plex Mono', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "rgba(84,84,88,0.2)" },
        horzLines: { color: "rgba(84,84,88,0.2)" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "rgba(240,180,41,0.4)", labelBackgroundColor: "#1B1B1F" },
        horzLine: { color: "rgba(240,180,41,0.4)", labelBackgroundColor: "#1B1B1F" },
      },
      rightPriceScale: {
        borderColor: "rgba(84,84,88,0.3)",
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        borderColor: "rgba(84,84,88,0.3)",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00C278",
      downColor: "#FF3333",
      borderUpColor: "#00C278",
      borderDownColor: "#FF3333",
      wickUpColor: "#00C278",
      wickDownColor: "#FF3333",
    });

    const volumeSeries = chart.addHistogramSeries({
      priceFormat: { type: "volume" },
      priceScaleId: "",
    });
    volumeSeries.priceScale().applyOptions({
      scaleMargins: { top: 0.8, bottom: 0 },
    });

    chartRef.current = chart;
    candleSeriesRef.current = candleSeries;
    volumeSeriesRef.current = volumeSeries;

    const ro = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        chart.applyOptions({ width, height });
      }
    });
    ro.observe(containerRef.current);

    return () => {
      ro.disconnect();
      if (intervalRef.current) clearInterval(intervalRef.current);
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // Load data when symbol/timeframe changes
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !volumeSeries || !chart) return;

    const abortCtrl = new AbortController();
    let active = true;
    lastTimeRef.current = 0;

    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    const loadCandles = async (candles: CandleRaw[]) => {
      try {
        const sorted = candles
          .filter((c) => c.time > 0)
          .sort((a, b) => a.time - b.time)
          .filter((c, i, arr) => i === 0 || c.time !== arr[i - 1].time);

        if (sorted.length === 0) {
          errorReasonRef.current = "no_data";
          setStatusSync("error");
          return;
        }

        const candleData: CandlestickData<Time>[] = sorted.map((c) => ({
          time: c.time as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }));
        const volumeData: HistogramData<Time>[] = sorted.map((c) => ({
          time: c.time as Time,
          value: c.volume,
          color: c.close >= c.open ? "rgba(0,194,120,0.15)" : "rgba(255,51,51,0.15)",
        }));
        candleSeries.setData(candleData);
        volumeSeries.setData(volumeData);
        lastTimeRef.current = sorted[sorted.length - 1].time;
        chart.timeScale().fitContent();
        setStatusSync("ok");
      } catch (err) {
        console.error("[TradingChart] setData failed:", err);
        errorReasonRef.current = "no_data";
        setStatusSync("error");
      }
    };

    const loadInitial = async () => {
      setStatusSync("loading");
      const candles = await fetchCandles();
      if (!active) return;
      if (!candles) {
        serverDownRef.current = true;
        errorReasonRef.current = "server_down";
        setStatusSync("error");
        return;
      }
      if (candles.length === 0) {
        errorReasonRef.current = "no_data";
        setStatusSync("error");
        return;
      }

      await loadCandles(candles);

      const overlays = await fetchOverlays();
      if (overlays && active) {
        if (overlays.markers.length > 0) {
          const sorted = overlays.markers
            .filter((m) => m.time > 0)
            .sort((a, b) => a.time - b.time)
            .map((m) => ({
              time: m.time as Time,
              position: m.position as "belowBar" | "aboveBar" | "inBar",
              color: m.color,
              shape: m.shape as "arrowUp" | "arrowDown" | "circle" | "square",
              text: m.text,
            }));
          candleSeries.setMarkers(sorted);
        }

        for (const pl of overlays.priceLines) {
          candleSeries.createPriceLine({
            price: pl.price,
            color: pl.color,
            lineWidth: pl.lineWidth as 1 | 2 | 3 | 4,
            lineStyle: pl.lineStyle as LineStyle,
            axisLabelVisible: true,
            title: pl.title,
          });
        }
      }

      const fibData = await fetchFibonacci();
      if (fibData && active) {
        if (fibData.golden_zone) {
          const gzLabel =
            (fibData.confluence.gz_fvg ? " + CE" : "") +
            (fibData.confluence.gz_ob ? " + OB" : "");
          candleSeries.createPriceLine({
            price: fibData.golden_zone.top,
            color: "#FF9F0A",
            lineWidth: 2 as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: `GZ 0.618${gzLabel}`,
          });
          candleSeries.createPriceLine({
            price: fibData.golden_zone.bottom,
            color: "#FF9F0A",
            lineWidth: 2 as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: "GZ 0.705",
          });
        }

        for (const level of fibData.levels) {
          if (level.ratio === 0.618 || level.ratio === 0.705) continue;
          candleSeries.createPriceLine({
            price: level.price,
            color: "rgba(142,142,147,0.5)",
            lineWidth: 1 as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `Fib ${level.label}`,
          });
        }
      }
    };

    loadInitial();

    intervalRef.current = setInterval(async () => {
      if (!active || serverDownRef.current) return;
      const candles = await fetchCandles();
      if (!candles || candles.length === 0) return;

      if (statusRef.current !== "ok") {
        await loadCandles(candles);
        return;
      }

      const latest = candles[candles.length - 1];
      if (latest.time >= lastTimeRef.current) {
        candleSeries.update({
          time: latest.time as Time,
          open: latest.open,
          high: latest.high,
          low: latest.low,
          close: latest.close,
        });
        volumeSeries.update({
          time: latest.time as Time,
          value: latest.volume,
          color: latest.close >= latest.open ? "rgba(0,194,120,0.15)" : "rgba(255,51,51,0.15)",
        });
        lastTimeRef.current = latest.time;
      }
    }, 5_000);

    return () => {
      active = false;
      abortCtrl.abort();
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [symbol, timeframe, count, fetchCandles, fetchOverlays, fetchFibonacci]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%", minHeight: 400 }}>
      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%", minHeight: 400 }}
      />
      {status !== "ok" && (
        <div style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: 10,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          background: "#0D0D0F",
          borderRadius: 4,
          gap: 12,
        }}>
          {status === "loading" ? (
            <>
              <div style={{
                width: 28,
                height: 28,
                border: "2px solid rgba(84,84,88,0.4)",
                borderTop: "2px solid #0A84FF",
                borderRadius: "50%",
                animation: "spin 0.8s linear infinite",
              }} />
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 13,
                color: "#8A8A93",
              }}>
                Loading chart data…
              </span>
            </>
          ) : (
            <>
              <span style={{ fontSize: 28, color: "#FF453A" }}>⚠</span>
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 15,
                fontWeight: 600,
                color: "#FF453A",
              }}>
                Chart unavailable
              </span>
              <span style={{
                fontFamily: "'IBM Plex Mono', monospace",
                fontSize: 13,
                color: "#8A8A93",
              }}>
                {errorReasonRef.current === "no_data"
                  ? "No candle data for this symbol / timeframe"
                  : "Bot candle server not reachable"}
              </span>
            </>
          )}
        </div>
      )}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  );
}
