import React from 'react';
import './XRayPanel.css';
import { BASE } from '../api';

export async function fetchRunSummary() {
  const r = await fetch(`${BASE}/run-summary`);
  if (!r.ok) throw new Error(`run-summary failed (${r.status})`);
  return r.json();
}

const TONE = { COMPROMISED: 'risk', BLOCKED: 'ok', DEFENDED: 'ok', SAFE: 'ok' };
const TITLE = { baseline: 'Baseline agent', camel: 'Protected agent' };

function InvoicePane({ input }) {
  const hidden = input?.hidden ?? [];
  return (
    <div className="xr-pane">
      <h3>What a person sees <span>{input?.kind}</span></h3>
      <pre className="xr-visible">{input?.visible_text || '(no visible text)'}</pre>
      <h3>Hidden in the same file</h3>
      <p className="xr-note">Invisible to people, readable by AI.</p>
      {hidden.length === 0 ? (
        <p className="xr-note">Nothing hidden found.</p>
      ) : (
        <ul className="xr-hidden">
          {hidden.map((h, i) => (
            <li key={i}>
              <div className="xr-tags">
                <b>{h.technique}</b>
                <span>in {h.where}</span>
              </div>
              <p>{h.text}</p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function AgentCard({ name, card }) {
  return (
    <div className="xr-pane xr-agent">
      <div className={`xr-banner xr-banner--${TONE[card.verdict] || 'neutral'}`}>
        <span>{TITLE[name] || name}</span>
        <strong>{card.verdict}</strong>
      </div>
      <p className="xr-decision">{card.decision}</p>
      <p>{card.headline}</p>
      {card.blocked_by?.map((b, i) => (
        <div className="xr-block" key={i}>
          <strong>{b.layer}</strong>
          <span>Tried: <code>{b.tool}</code></span>
          <span>Why: {b.reason}</span>
        </div>
      ))}
      {card.payments?.length > 0 && (
        <ul className="xr-pay">
          {card.payments.map((p) => (
            <li key={p.transaction_id}>
              {p.vendor_id}: INR {Number(p.amount).toLocaleString()} to <code>{p.account_number}</code>
            </li>
          ))}
        </ul>
      )}
      {card.error && <p className="xr-error">Agent error: {card.error}</p>}
    </div>
  );
}

export default function XRayPanel({ summary, error }) {
  if (error) return <div className="xr-empty xr-empty--error">Could not load the run summary: {error}</div>;
  if (!summary) return <div className="xr-empty">Fire an attack to see the invoice X-ray.</div>;
  const { attack, input, agents } = summary;
  return (
    <section className="xr" aria-label="Invoice X-ray">
      <h3 className="xr-title">Invoice X-ray: {attack?.name}</h3>
      <div className="xr-grid">
        <InvoicePane input={input} />
        <div className="xr-col">
          {['baseline', 'camel'].filter((n) => agents?.[n]).map((n) => (
            <AgentCard key={n} name={n} card={agents[n]} />
          ))}
        </div>
      </div>
    </section>
  );
}
