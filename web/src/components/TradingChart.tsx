"use client";

import { useEffect, useRef, useCallback } from "react";
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

  // Fetch candles from API
  const fetchCandles = useCallback(async () => {
    try {
      const res = await fetch(
        `/api/candles?symbol=${encodeURIComponent(symbol)}&timeframe=${encodeURIComponent(timeframe)}&count=${count}`
      );
      if (!res.ok) return null;
      return (await res.json()) as CandleRaw[];
    } catch {
      return null;
    }
  }, [symbol, timeframe, count]);

  // Fetch trade overlays
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

  // Fetch Fibonacci levels
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

    // Clean up previous chart
    if (chartRef.current) {
      chartRef.current.remove();
      chartRef.current = null;
    }

    const chart = createChart(containerRef.current, {
      layout: {
        background: { type: ColorType.Solid, color: "#0a0a0a" },
        textColor: "#00cc33",
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontSize: 11,
      },
      grid: {
        vertLines: { color: "#1a1a1a" },
        horzLines: { color: "#1a1a1a" },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: "#00ff4180", labelBackgroundColor: "#111111" },
        horzLine: { color: "#00ff4180", labelBackgroundColor: "#111111" },
      },
      rightPriceScale: {
        borderColor: "#1a1a1a",
        scaleMargins: { top: 0.1, bottom: 0.25 },
      },
      timeScale: {
        borderColor: "#1a1a1a",
        timeVisible: true,
        secondsVisible: false,
      },
    });

    const candleSeries = chart.addCandlestickSeries({
      upColor: "#00ff41",
      downColor: "#ff4444",
      borderUpColor: "#00ff41",
      borderDownColor: "#ff4444",
      wickUpColor: "#00cc33",
      wickDownColor: "#cc3333",
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

    // Handle resize
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
  }, []); // Mount once

  // Load data when symbol/timeframe changes
  useEffect(() => {
    const candleSeries = candleSeriesRef.current;
    const volumeSeries = volumeSeriesRef.current;
    const chart = chartRef.current;
    if (!candleSeries || !volumeSeries || !chart) return;

    let active = true;
    lastTimeRef.current = 0;

    // Clear previous interval
    if (intervalRef.current) {
      clearInterval(intervalRef.current);
      intervalRef.current = null;
    }

    const loadInitial = async () => {
      const candles = await fetchCandles();
      if (!candles || !active) return;

      const candleData: CandlestickData<Time>[] = candles.map((c) => ({
        time: c.time as Time,
        open: c.open,
        high: c.high,
        low: c.low,
        close: c.close,
      }));

      const volumeData: HistogramData<Time>[] = candles.map((c) => ({
        time: c.time as Time,
        value: c.volume,
        color: c.close >= c.open ? "#00ff4130" : "#ff444430",
      }));

      candleSeries.setData(candleData);
      volumeSeries.setData(volumeData);

      if (candles.length > 0) {
        lastTimeRef.current = candles[candles.length - 1].time;
      }

      chart.timeScale().fitContent();

      // Load trade overlays
      const overlays = await fetchOverlays();
      if (overlays && active) {
        // Apply markers
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

        // Apply price lines for open trades
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

      // Load Fibonacci levels
      const fibData = await fetchFibonacci();
      if (fibData && active) {
        // Golden Zone — amber highlight lines
        if (fibData.golden_zone) {
          const gzLabel =
            (fibData.confluence.gz_fvg ? " + CE" : "") +
            (fibData.confluence.gz_ob ? " + OB" : "");
          candleSeries.createPriceLine({
            price: fibData.golden_zone.top,
            color: "#f59e0b",
            lineWidth: 2 as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: `GZ 0.618${gzLabel}`,
          });
          candleSeries.createPriceLine({
            price: fibData.golden_zone.bottom,
            color: "#f59e0b",
            lineWidth: 2 as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Solid,
            axisLabelVisible: true,
            title: "GZ 0.705",
          });
        }

        // Individual Fib levels (non-GZ ones as gray dashed)
        for (const level of fibData.levels) {
          if (level.ratio === 0.618 || level.ratio === 0.705) continue; // already drawn as GZ
          candleSeries.createPriceLine({
            price: level.price,
            color: "#666666",
            lineWidth: 1 as 1 | 2 | 3 | 4,
            lineStyle: LineStyle.Dashed,
            axisLabelVisible: true,
            title: `Fib ${level.label}`,
          });
        }
      }
    };

    loadInitial();

    // Poll for new candles every 5 seconds
    intervalRef.current = setInterval(async () => {
      if (!active) return;
      const candles = await fetchCandles();
      if (!candles || candles.length === 0) return;

      // Only update the last candle (live bar) or append new ones
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
          color: latest.close >= latest.open ? "#00ff4130" : "#ff444430",
        });
        lastTimeRef.current = latest.time;
      }
    }, 5_000);

    return () => {
      active = false;
      if (intervalRef.current) {
        clearInterval(intervalRef.current);
        intervalRef.current = null;
      }
    };
  }, [symbol, timeframe, count, fetchCandles, fetchOverlays, fetchFibonacci]);

  return (
    <div
      ref={containerRef}
      style={{ width: "100%", height: "100%", minHeight: 400, borderRadius: 6, border: "1px solid #1c1c28" }}
    />
  );
}
