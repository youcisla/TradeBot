import React, { useState } from 'react';

type CommandButtonProps = {
  children: React.ReactNode;
  onClick: () => void | Promise<void>;
  variant?: 'danger' | 'warning' | 'info';
  confirmMessage?: string;
  className?: string;
};

export const CommandButton = ({ children, onClick, variant = 'danger', confirmMessage = "Are you sure?", className = '' }: CommandButtonProps) => {
  const [confirming, setConfirming] = useState(false);
  const [loading, setLoading] = useState(false);

  const styles = {
    danger: "bg-red text-white hover:bg-red/80",
    warning: "border border-orange text-orange hover:bg-orange/10",
    info: "border border-cyan text-cyan hover:bg-cyan/10",
  };

  const handlePress = async () => {
    if (!confirming) {
      setConfirming(true);
      setTimeout(() => setConfirming(false), 3000);
      return;
    }
    setLoading(true);
    try {
      await onClick();
    } finally {
      setLoading(false);
      setConfirming(false);
    }
  };

  return (
    <button 
      onClick={handlePress}
      disabled={loading}
      className={`px-6 py-3 font-ui font-bold uppercase tracking-wider rounded-sm transition-all focus:outline-none ${styles[variant]} ${className}`}
    >
      {loading ? 'Processing...' : confirming ? confirmMessage : children}
    </button>
  );
};
