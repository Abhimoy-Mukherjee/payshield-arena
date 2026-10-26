import React from 'react';

const CONFIG = {
  COMPROMISED: { tone: 'risk', label: 'Compromised', sub: 'The payment instruction was redirected.', icon: '!' },
  BLOCKED: { tone: 'protected', label: 'Blocked', sub: 'A guardrail stopped the suspicious action.', icon: '✓' },
  SAFE: { tone: 'safe', label: 'Safe', sub: 'No suspicious payment was executed.', icon: '○' },
  PENDING: { tone: 'pending', label: 'Awaiting run', sub: 'Start a scenario to see the outcome.', icon: '—' },
  ERROR: { tone: 'error', label: 'Unavailable', sub: 'The simulator did not return a result.', icon: '!' },
  UNKNOWN: { tone: 'pending', label: 'Unknown result', sub: 'This agent did not return a verdict.', icon: '?' },
};

export default function VerdictBanner({ verdict }) {
  const result = CONFIG[verdict] || CONFIG.PENDING;
  return (
    <div className={`verdict-banner verdict-banner--${result.tone}`} role="status" aria-live="polite">
      <span className="verdict-icon" aria-hidden="true">{result.icon}</span>
      <span className="verdict-copy"><strong>{result.label}</strong><span>{result.sub}</span></span>
      <span className="verdict-arrow" aria-hidden="true">↗</span>
    </div>
  );
}
