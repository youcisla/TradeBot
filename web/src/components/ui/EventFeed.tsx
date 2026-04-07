import React, { useRef, useEffect } from 'react';
import { AgentBadge, LevelBadge } from './Badges';

export type FeedEvent = {
  id: string;
  timestamp: string;
  agent: string;
  level: string;
  message: string;
  data?: any;
};

type EventFeedProps = {
  events: FeedEvent[];
  onPauseToggle?: (paused: boolean) => void;
};

export const EventFeed = ({ events, onPauseToggle }: EventFeedProps) => {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Auto scroll bottom when new events arrive
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [events.length]);

  return (
    <div className="flex flex-col bg-bg-2 border border-border rounded-sm h-[400px]">
       <div className="flex-1 overflow-y-auto p-4 space-y-1 font-mono text-xs" ref={scrollRef}>
          {events.map((ev) => {
            const date = new Date(ev.timestamp);
            const timeStr = date.toLocaleTimeString('en-US', { hour12: false, hour: '2-digit', minute:'2-digit', second:'2-digit' });
            
            let color = 'text-text-2';
            if (ev.level === 'warn') color = 'text-orange';
            if (ev.level === 'error') color = 'text-red';
            
            return (
              <div key={ev.id} className={`flex items-start gap-3 hover:bg-bg-4 group px-2 py-1 rounded-sm transition-colors ${color}`}>
                <span className="text-text-3 shrink-0">{timeStr}</span>
                <span className="shrink-0"><AgentBadge agent={ev.agent} /></span>
                <span className="shrink-0"><LevelBadge level={ev.level} /></span>
                <span className="break-words flex-1 group-hover:text-text-1 transition-colors">{ev.message}</span>
              </div>
            );
          })}
          {events.length === 0 && <div className="text-text-3 italic font-ui">No events recorded</div>}
       </div>
    </div>
  );
};
