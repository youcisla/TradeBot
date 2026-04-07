import React from 'react';

export const Skeleton = ({ className = '', style }: { className?: string, style?: React.CSSProperties }) => (
  <div className={`animate-pulse bg-bg-3 rounded-sm ${className}`} style={style} />
);
