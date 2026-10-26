import React from 'react';
import AgentLog from './AgentLog';
import VerdictBanner from './VerdictBanner';

export default function AgentPanel({ title, subtitle, variant, steps, verdict, running }) {
  const stateLabel = running ? 'RUNNING' : verdict === 'ERROR' ? 'UNAVAILABLE' : verdict === 'UNKNOWN' ? 'UNKNOWN' : verdict ? 'COMPLETE' : 'STANDBY';
  return (
    <article className={`agent-panel agent-panel--${variant}`}>
      <header className="agent-header">
        <span className="agent-avatar" aria-hidden="true">
          {variant === 'protected' ? (
            <svg viewBox="0 0 32 32" fill="none"><path d="M16 3.5 26 7v7.1c0 6.3-4.1 11.3-10 14.4C10.1 25.4 6 20.4 6 14.1V7l10-3.5Z" /><path d="m11.5 15.7 3 3 6-6.2" /></svg>
          ) : <span>01</span>}
        </span>
        <div className="agent-heading-copy">
          <span className="agent-index">{variant === 'protected' ? 'AGENT 02' : 'AGENT 01'}</span>
          <h3>{title}</h3>
          <p>{subtitle}</p>
        </div>
        <span className={`agent-state${running ? ' is-running' : ''}${verdict === 'ERROR' ? ' agent-state--error' : verdict === 'UNKNOWN' ? ' agent-state--unknown' : ''}`}>
          <span className="agent-state-dot" />{stateLabel}
        </span>
      </header>
      <div className="agent-log-heading"><span>ACTIVITY TRACE</span><span>{steps.length.toString().padStart(2, '0')} EVENTS</span></div>
      <AgentLog steps={steps} running={running} />
      <div className="agent-verdict-wrap">
        <span className="verdict-caption">OUTCOME</span>
        <VerdictBanner verdict={verdict} />
      </div>
    </article>
  );
}
