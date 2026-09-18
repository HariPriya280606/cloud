import React from 'react';
import { CloudRain, RefreshCw, Cpu } from 'lucide-react';

export default function Header({ onReset, isResetting }) {
  return (
    <header className="header-card">
      <div className="header-title-group">
        <h1>
          <CloudRain size={32} color="#38bdf8" />
          Cloud Bill That Wouldn't Stop Growing
        </h1>
        <p className="header-subtitle">
          Autonomous Cloud Cost Optimization Agent with Deterministic Safety Verification
        </p>
      </div>
      <div className="header-actions">
        <div className="status-indicator">
          <div className="status-dot"></div>
          <span>Autonomous Agent Ready</span>
        </div>
        <button 
          className="btn-secondary" 
          onClick={onReset} 
          disabled={isResetting}
          title="Reset simulator and telemetry state"
        >
          <RefreshCw size={14} className={isResetting ? "animate-spin" : ""} style={{ marginRight: '6px' }} />
          Reset Environment
        </button>
      </div>
    </header>
  );
}
