"use client";

import { useState, useEffect } from "react";
import TradingChart from "@/components/TradingChart";
import { Card, CardBody, CardHeader } from "@/components/ui/Card";
import { ArcGauge } from "@/components/ui/ArcGauge";
import { EventFeed, FeedEvent } from "@/components/ui/EventFeed";

export default function MarketIntel() {
  const [symbol, setSymbol] = useState("BTC/USD");
  const [timeframe, setTimeframe] = useState("15m");
  
  // Overlays state (not yet fully connected to Chart, but UI ready)
  const [showFVG, setShowFVG] = useState(true);
  const [showOB, setShowOB] = useState(true);
  const [showFIB, setShowFIB] = useState(false);

  // Symbol Events
  const [events, setEvents] = useState<FeedEvent[]>([]);

  useEffect(() => {
    let active = true;
    const fetchEm = async () => {
      try {
        const res = await fetch("/api/events?limit=50");
        const data = await res.json();
        if (active && Array.isArray(data)) {
          // simple filter map
          const mapped: FeedEvent[] = [];
          for (let i = 0; i < data.length; i++) {
            const e = data[i];
            const m = (e.message || e.msg || "").toLowerCase();
            const s = symbol.split("/")[0].toLowerCase();
            if (m.includes(s) || m.includes("all markets")) {
               mapped.push({
                 id: String(e.id || Math.random()),
                 timestamp: String(e.ts || e.created_at || new Date().toISOString()),
                 agent: String(e.agent || 'SYSTEM'),
                 level: String(e.level || 'info').toLowerCase(),
                 message: String(e.message || e.msg || ''),
               });
            }
          }
          setEvents(mapped.slice(0, 50));
        }
      } catch (err) {}
    };
    fetchEm();
    const inv = setInterval(fetchEm, 5000);
    return () => { active = false; clearInterval(inv); };
  }, [symbol]);

  return (
    <div className="flex flex-col h-[calc(100vh-52px)] overflow-hidden p-4 md:p-6 lg:p-8 gap-6 max-w-[1800px] mx-auto">
      {/* Top Toolbar */}
      <div className="flex items-center gap-6 p-4 bg-bg-2 border border-border rounded-sm shrink-0">
        <select 
          value={symbol}
          onChange={e => setSymbol(e.target.value)}
          className="bg-bg-3 border border-border text-text-1 font-mono font-bold text-lg px-4 py-2 rounded-sm focus:outline-none"
        >
          <option value="BTC/USD">BTC/USD</option>
          <option value="ETH/USD">ETH/USD</option>
          <option value="SOL/USD">SOL/USD</option>
        </select>

        <div className="flex gap-1 bg-bg-3 p-1 rounded-sm border border-border">
          {["1m", "5m", "15m", "1h", "4h", "1d", "1w"].map(tf => (
            <button
              key={tf}
              onClick={() => setTimeframe(tf)}
              className={`px-3 py-1.5 font-ui text-xs font-bold uppercase tracking-wider rounded-sm transition-colors ${timeframe === tf ? "bg-bg-4 text-text-1 shadow-sm" : "text-text-3 hover:text-text-2"}`}
            >
              {tf}
            </button>
          ))}
        </div>

        <div className="h-6 w-px bg-border mx-2" />

        <div className="flex gap-2">
          {[{id: "fvg", label: "FVG", val: showFVG, set: setShowFVG}, 
            {id: "ob", label: "Order Blocks", val: showOB, set: setShowOB}, 
            {id: "fib", label: "Fibonacci", val: showFIB, set: setShowFIB}
           ].map(o => (
            <button
              key={o.id}
              onClick={() => o.set(!o.val)}
              className={`px-4 py-1.5 font-ui text-xs font-bold tracking-wider rounded-sm border transition-colors ${o.val ? "bg-gold-dim border-gold text-gold" : "bg-bg-3 border-border text-text-3 hover:text-text-2"}`}
            >
              {o.label}
            </button>
          ))}
        </div>
      </div>

      {/* Main Content */}
      <div className="flex flex-1 min-h-0 gap-6">
        {/* Left: Chart + Events */}
        <div className="flex-1 flex flex-col gap-6 min-w-0">
          <div className="flex-1 bg-bg-1 border border-border rounded-sm relative overflow-hidden">
            {/* The TradingChart expects its container to have relative + size. We give it flex-1. */}
            <div className="absolute inset-0">
              <TradingChart symbol={symbol} timeframe={timeframe} />
            </div>
          </div>
          
          {/* Bottom Strip: Agent events for symbol */}
          <div className="h-48 border border-border rounded-sm shrink-0 bg-bg-2 p-4 flex flex-col">
             <h3 className="font-ui text-xs font-bold tracking-widest text-text-3 uppercase mb-4 shrink-0">
                Activity Stream: {symbol}
             </h3>
             <div className="flex-1 min-h-0">
               <EventFeed events={events} />
             </div>
          </div>
        </div>

        {/* Right: Stats Panel */}
        <div className="w-[300px] shrink-0 flex flex-col gap-4 overflow-y-auto">
           <Card>
             <CardHeader>Live Market Stats</CardHeader>
             <CardBody className="space-y-6">
                <div className="flex justify-between items-center pb-4 border-b border-border/50">
                   <div className="flex flex-col">
                      <span className="text-[10px] uppercase text-text-3 font-bold tracking-widest">Bid</span>
                      <span className="font-mono text-text-1">98,241.50</span>
                   </div>
                   <div className="flex flex-col text-right">
                      <span className="text-[10px] uppercase text-text-3 font-bold tracking-widest">Ask</span>
                      <span className="font-mono text-text-1">98,242.00</span>
                   </div>
                </div>
                
                <div className="flex justify-between items-center pb-4 border-b border-border/50">
                   <span className="text-xs uppercase text-text-3 font-bold tracking-widest">Session</span>
                   <span className="px-2 py-0.5 bg-blue-dim text-blue font-bold rounded-sm text-[10px] uppercase tracking-wider">New York</span>
                </div>

                <div className="space-y-2 pb-4 border-b border-border/50">
                   <div className="flex justify-between">
                     <span className="text-xs uppercase text-text-3 font-bold tracking-widest">Daily Range</span>
                     <span className="font-mono text-xs text-text-2">2.4%</span>
                   </div>
                   <div className="h-1.5 w-full bg-bg-4 rounded-sm overflow-hidden relative">
                     <div className="absolute left-[20%] right-[30%] bg-text-3 h-full opacity-50" />
                     <div className="absolute left-[65%] w-1.5 h-full bg-gold" />
                   </div>
                   <div className="flex justify-between text-[10px] font-mono text-text-3">
                     <span>$96,000</span>
                     <span>$99,200</span>
                   </div>
                </div>

                <div className="flex flex-col items-center pb-4 border-b border-border/50">
                  <span className="text-xs uppercase text-text-3 font-bold tracking-widest w-full text-left mb-2">RSI (14)</span>
                  <div className="w-32 h-20 -mb-4">
                    <ArcGauge value={62} max={100} label="" />
                  </div>
                </div>

                <div className="flex justify-between items-center">
                   <span className="text-xs uppercase text-text-3 font-bold tracking-widest">ICT Signal</span>
                   <span className="px-2 py-1 bg-gold-dim text-gold font-bold font-mono text-xs rounded-sm">LONG (92%)</span>
                </div>
             </CardBody>
           </Card>
        </div>
      </div>
    </div>
  );
}
