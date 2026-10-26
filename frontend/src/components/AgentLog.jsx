import React, { useEffect, useRef } from 'react';

function StepRow({ step }) {
  const label = step.label || '';
  if (label === 'plan_locked') {
    return <div className="trace-row trace-row--plan"><span className="trace-marker" aria-hidden="true">◇</span><div><strong>Plan set · {step.detail?.steps} steps</strong><p>{step.detail?.goal}</p></div></div>;
  }
  if (label.startsWith('blocked:')) {
    const tool = label.split(':')[1];
    return <div className="trace-row trace-row--blocked"><span className="trace-marker" aria-hidden="true">×</span><div><strong>Action stopped · {tool}()</strong><p>{typeof step.detail === 'string' ? step.detail.slice(0, 140) : ''}</p></div></div>;
  }
  if (label.startsWith('tool_result:')) {
    const tool = label.split(':')[1];
    const trust = step.detail?.__trust;
    const tone = trust === 'UNTRUSTED' ? 'warning' : trust === 'TRUSTED' ? 'trusted' : 'neutral';
    return <div className={`trace-row trace-row--${tone}`}><span className="trace-marker" aria-hidden="true">{trust === 'UNTRUSTED' ? '!' : trust === 'TRUSTED' ? '✓' : '·'}</span><div><strong>{tool}()</strong><span className="trace-detail">{trust || 'complete'}</span></div></div>;
  }
  if (label.startsWith('tool_call:')) {
    const tool = label.split(':')[1];
    const args = step.detail || {};
    const argString = Object.entries(args).filter(([key]) => key !== '__trust').map(([key, value]) => `${key}=${JSON.stringify(value).slice(0, 24)}`).join(', ');
    return <div className="trace-row trace-row--call"><span className="trace-marker" aria-hidden="true">↗</span><div><strong>{tool}()</strong><span className="trace-detail">{argString}</span></div></div>;
  }
  if (label === 'injection_detected') {
    return <div className="trace-row trace-row--warning"><span className="trace-marker" aria-hidden="true">!</span><div><strong>Suspicious instruction detected</strong><p>Adversarial content was flagged before the payment action.</p></div></div>;
  }
  if (label === 'planning') {
    return <div className="trace-row trace-row--planning"><span className="trace-marker" aria-hidden="true">◌</span><div><strong>Reviewing the request…</strong></div></div>;
  }
  if (label === 'planner_error') {
    return <div className="trace-row trace-row--blocked"><span className="trace-marker" aria-hidden="true">!</span><div><strong>Review could not complete</strong><p>{String(step.detail || '').slice(0, 100)}</p></div></div>;
  }
  const detail = step.detail ? typeof step.detail === 'object' ? JSON.stringify(step.detail).slice(0, 100) : String(step.detail).slice(0, 100) : '';
  return <div className="trace-row trace-row--call"><span className="trace-marker" aria-hidden="true">·</span><div><strong>{label || 'Update'}</strong>{detail && <span className="trace-detail">{detail}</span>}</div></div>;
}

export default function AgentLog({ steps, running }) {
  const ref = useRef(null);
  useEffect(() => { if (ref.current) ref.current.scrollTop = ref.current.scrollHeight; }, [steps]);
  return (
    <div ref={ref} className="agent-log" aria-label="Agent activity trace" aria-live="polite">
      {steps.length === 0 && <div className="trace-empty"><span className="trace-empty-mark" aria-hidden="true">⌁</span><span>Agent activity will appear here.</span></div>}
      {steps.map((step, index) => <StepRow key={`${step.label || 'step'}-${index}`} step={step} />)}
      {running && <span className="trace-cursor" aria-label="Processing" />}
    </div>
  );
}
