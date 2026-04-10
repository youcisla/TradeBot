import React from 'react';

type CardProps = {
  children: React.ReactNode;
  variant?: 'default' | 'elevated' | 'ghost';
  accent?: 'gold' | 'cyan' | 'red' | 'none';
  className?: string;
  style?: React.CSSProperties;
};

export const Card = ({ children, variant = 'default', accent = 'none', className = '', style }: CardProps) => {
  const baseStyle = "rounded-sm overflow-hidden border border-border";

  const variantStyles = {
    default: "bg-bg-2",
    elevated: "bg-bg-3 shadow-md",
    ghost: "bg-transparent border-transparent",
  };

  const accentStyles = {
    none: "",
    gold: "border-l-4 border-l-gold",
    cyan: "border-l-4 border-l-cyan",
    red: "border-l-4 border-l-red",
  };

  return (
    <div className={`${baseStyle} ${variantStyles[variant]} ${accentStyles[accent]} ${className}`} style={style}>
      {children}
    </div>
  );
};

export const CardHeader = ({ children, className = '', style }: { children: React.ReactNode, className?: string, style?: React.CSSProperties }) => (
  <div className={`px-4 py-3 border-b border-border text-ui uppercase text-text-2 text-sm tracking-wider ${className}`} style={style}>
    {children}
  </div>
);

export const CardBody = ({ children, className = '', style }: { children: React.ReactNode; className?: string; style?: React.CSSProperties }) => (
  <div className={`p-4 ${className}`} style={style}>
    {children}
  </div>
);
