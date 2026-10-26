import React, { useCallback, useEffect, useRef, useState } from 'react';
import AttackPanel from './components/AttackPanel';
import AgentPanel from './components/AgentPanel';
import TransactionLedger from './components/TransactionLedger';
import { runAttack, fetchLedger, resetArena, streamAgent } from './api';

const INITIAL = { steps: [], verdict: null, running: false };

export default function App() {
  const [baseline, setBaseline] = useState(INITIAL);
  const [protectedAgent, setProtectedAgent] = useState(INITIAL);
  const [ledger, setLedger] = useState([]);
  const [running, setRunning] = useState(false);
  const cleanupRef = useRef([]);

  const stopStreams = useCallback(() => {
    cleanupRef.current.forEach((stop) => stop());
    cleanupRef.current = [];
  }, []);

  useEffect(() => () => stopStreams(), [stopStreams]);

  useEffect(() => {
    let active = true;
    fetchLedger()
      .then((result) => { if (active) setLedger(result.transactions || []); })
      .catch(() => {});
    return () => { active = false; };
  }, []);

  const handleReset = useCallback(async () => {
    stopStreams();
    setBaseline(INITIAL);
    setProtectedAgent(INITIAL);
    setRunning(false);
    try {
      await resetArena();
      const result = await fetchLedger();
      setLedger(result.transactions || []);
    } catch {
      // Preserve the last known records if the service is temporarily unavailable.
    }
  }, [stopStreams]);

  const handleFire = useCallback(async (attackId, instruction) => {
    stopStreams();
    setBaseline({ steps: [], verdict: null, running: true });
    setProtectedAgent({ steps: [], verdict: null, running: true });
    setRunning(true);

    const stopBaseline = streamAgent(
      'baseline',
      (step) => setBaseline((current) => ({ ...current, steps: [...current.steps, step] })),
      () => setBaseline((current) => ({ ...current, running: false }))
    );
    const stopProtected = streamAgent(
      'camel',
      (step) => setProtectedAgent((current) => ({ ...current, steps: [...current.steps, step] })),
      () => setProtectedAgent((current) => ({ ...current, running: false }))
    );
    cleanupRef.current = [stopBaseline, stopProtected];

    let result;
    try {
      result = await runAttack(attackId, instruction);
      if (!Array.isArray(result?.results)) throw new Error('No agent results returned');
    } catch {
      stopStreams();
      setBaseline((current) => ({ ...current, verdict: 'ERROR', running: false }));
      setProtectedAgent((current) => ({ ...current, verdict: 'ERROR', running: false }));
      setRunning(false);
      return;
    }

    const baselineVerdict = result.results.find((item) => item.agent === 'baseline')?.verdict || 'UNKNOWN';
    const protectedVerdict = result.results.find((item) => item.agent === 'camel')?.verdict || 'UNKNOWN';
    setBaseline((current) => ({ ...current, verdict: baselineVerdict, running: false }));
    setProtectedAgent((current) => ({ ...current, verdict: protectedVerdict, running: false }));
    try {
      const ledgerResult = await fetchLedger();
      setLedger(ledgerResult.transactions || []);
    } catch {
      // Keep the last known ledger if its refresh fails.
    }
    setRunning(false);
  }, [stopStreams]);

  return (
    <main className="app-shell" id="top">
      <header className="topbar">
        <a className="brand" href="#top" aria-label="PayShield Arena home">
          <span className="brand-mark" aria-hidden="true">
            <svg viewBox="0 0 32 32" fill="none">
              <path d="M16 3.5 26 7v7.1c0 6.3-4.1 11.3-10 14.4C10.1 25.4 6 20.4 6 14.1V7l10-3.5Z" />
              <path d="m11.5 15.7 3 3 6-6.2" />
            </svg>
          </span>
          <span className="brand-wordmark">PayShield<span>Arena</span></span>
        </a>
        <nav className="main-nav" aria-label="Main navigation">
          <a className="nav-link is-current" href="#overview">Overview</a>
          <a className="nav-link" href="#arena">Scenario lab</a>
          <a className="nav-link" href="#results">Agent comparison</a>
          <a className="nav-link" href="#ledger">Ledger</a>
        </nav>
        <div className="topbar-right" aria-label="System status">
          <span className="status-indicator" />
          <span>{running ? 'SIMULATION LIVE' : 'SYSTEM READY'}</span>
        </div>
      </header>

      <section className="hero" id="overview">
        <div className="hero-copy">
          <div className="eyebrow"><span className="eyebrow-mark" /> PAYMENT SECURITY, IN MOTION</div>
          <h1>Keep trust in<br /><span>the right hands.</span></h1>
          <p>Put payment agents to the test. See how a single instruction can change a transaction—and watch a stronger policy hold the line.</p>
          <div className="hero-actions">
            <a className="hero-cta" href="#arena">Explore the arena <span aria-hidden="true">↘</span></a>
            <div className="hero-proof"><span className="proof-symbol" aria-hidden="true">✓</span> Two agents. One clear result.</div>
          </div>
        </div>
        <div className="hero-art" aria-hidden="true">
          <div className="art-halo" />
          <div className="art-orbit art-orbit--one" />
          <div className="art-orbit art-orbit--two" />
          <div className="art-ring art-ring--outer" />
          <div className="art-ring art-ring--inner" />
          <div className="hero-shield">
            <svg viewBox="0 0 64 72" fill="none">
              <path d="M32 4 55 12v16c0 16-9.7 29-23 38C18.7 57 9 44 9 28V12L32 4Z" />
              <path d="m22 33 7 7 14-15" />
            </svg>
          </div>
          <div className="art-label art-label--top"><span className="label-dot" /> POLICY ACTIVE</div>
          <div className="art-label art-label--bottom"><span>02</span> AGENTS IN THE ARENA</div>
          <span className="cipher-bit cipher-bit--one">0x7A</span>
          <span className="cipher-bit cipher-bit--two">01 / 10</span>
          <span className="cipher-bit cipher-bit--three">⌘</span>
          <div className="art-crosshair art-crosshair--one" />
          <div className="art-crosshair art-crosshair--two" />
        </div>
      </section>

      <section className="workspace-section" id="arena">
        <div className="section-heading">
          <div>
            <span className="section-kicker">01 / THE ARENA</span>
            <h2>Choose a scenario. See what happens.</h2>
          </div>
          <p>Test a routine payment or challenge the agent with an injected instruction.</p>
        </div>
        <div className="attack-panel-wrap">
          <AttackPanel onFire={handleFire} onReset={handleReset} running={running} />
        </div>
      </section>

      <section className="results-section" id="results">
        <div className="section-heading section-heading--results">
          <div>
            <span className="section-kicker">02 / SIDE BY SIDE</span>
            <h2>One payment. Two paths.</h2>
          </div>
          <span className={`comparison-note${running ? ' is-running' : ''}`}>
            <span className="status-indicator" />
            {running ? 'COMPARISON IN PROGRESS' : 'READY WHEN YOU ARE'}
          </span>
        </div>
        <div className="agent-grid">
          <div className="agent-card baseline-card">
            <AgentPanel title="Baseline agent" subtitle="No added payment guardrails" variant="baseline" steps={baseline.steps} verdict={baseline.verdict} running={baseline.running} />
          </div>
          <div className="agent-card protected-card">
            <AgentPanel title="Protected agent" subtitle="Policy checks before every action" variant="protected" steps={protectedAgent.steps} verdict={protectedAgent.verdict} running={protectedAgent.running} />
          </div>
        </div>
      </section>

      <section className="ledger-wrap" id="ledger" aria-label="Transaction ledger">
        <TransactionLedger transactions={ledger} />
      </section>

      <footer className="footer">
        <a className="footer-brand" href="#top">PayShield Arena</a>
        <span>Simulated transactions <i /> Live policy comparison</span>
        <a className="back-to-top" href="#top">Back to top ↑</a>
      </footer>
    </main>
  );
}
