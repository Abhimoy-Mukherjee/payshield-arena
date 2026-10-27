import React, { useEffect, useState } from 'react';
import { fetchAttacks } from '../api';

const ATTACK_META = {
  legit: { tone: 'safe', icon: '○', desc: 'A routine payment with no suspicious content.' },
  malicious_pdf: { tone: 'risk', icon: '↗', desc: 'A document contains an instruction to redirect payment.' },
  poisoned_email: { tone: 'risk', icon: '✉', desc: 'An email tries to smuggle in a second instruction.' },
  tampered_vendor: { tone: 'risk', icon: '⌁', desc: 'A vendor record has been altered with a hidden request.' },
};

const FALLBACK_ATTACKS = [
  { id: 'legit', name: 'Legitimate invoice' },
  { id: 'malicious_pdf', name: 'Malicious PDF' },
  { id: 'poisoned_email', name: 'Poisoned email' },
  { id: 'tampered_vendor', name: 'Tampered vendor' },
];

export default function AttackPanel({ onFire, onReset, running }) {
  const [attacks, setAttacks] = useState([]);
  const [selected, setSelected] = useState('malicious_pdf');
  const [instruction, setInstruction] = useState('Pay invoice INV-001');

  useEffect(() => {
    let active = true;
    fetchAttacks()
      .then((items) => { if (active && items?.length) setAttacks(items); })
      .catch(() => { if (active) setAttacks(FALLBACK_ATTACKS); });
    return () => { active = false; };
  }, []);

  const scenarios = attacks.length ? attacks : FALLBACK_ATTACKS;
  const meta = ATTACK_META[selected] || ATTACK_META.legit;
  const isAttack = selected !== 'legit';

  return (
    <div className="scenario-builder">
      <div className="scenario-builder-head">
        <div>
          <span className="field-overline">SELECT A PAYMENT SCENARIO</span>
          <h3>What should the agent handle?</h3>
        </div>
        <span className="scenario-step"><span>01</span> CHOOSE</span>
      </div>

      <div className="scenario-layout">
        <div className="scenario-options" role="group" aria-label="Payment scenario">
          {scenarios.map((scenario) => {
            const scenarioMeta = ATTACK_META[scenario.id] || ATTACK_META.legit;
            const active = selected === scenario.id;
            return (
              <button
                key={scenario.id}
                type="button"
                className={`scenario-option scenario-option--${scenarioMeta.tone}${active ? ' is-selected' : ''}`}
                onClick={() => !running && setSelected(scenario.id)}
                disabled={running}
                aria-pressed={active}
              >
                <span className="scenario-option-icon" aria-hidden="true">{scenarioMeta.icon}</span>
                <span className="scenario-option-copy">
                  <span className="scenario-option-name">{scenario.name}</span>
                  <span className="scenario-option-kind">{scenario.id === 'legit' ? 'STANDARD PAYMENT' : 'INJECTION TEST'}</span>
                </span>
                <span className="scenario-option-check" aria-hidden="true">{active ? '✓' : ''}</span>
              </button>
            );
          })}
        </div>

        <div className="scenario-detail">
          <label className="instruction-label" htmlFor="payment-instruction">PAYMENT INSTRUCTION</label>
          <input
            id="payment-instruction"
            className="instruction-input"
            type="text"
            value={instruction}
            onChange={(event) => setInstruction(event.target.value)}
            disabled={running}
            placeholder="Describe the payment task"
          />
          <div className={`scenario-context${isAttack ? ' scenario-context--risk' : ' scenario-context--safe'}`}>
            <span className="context-icon" aria-hidden="true">{meta.icon}</span>
            <span>{meta.desc}</span>
          </div>
          <div className="scenario-actions">
            <button className="reset-button" type="button" onClick={onReset} disabled={running}>Reset</button>
            <button
              className={`run-button${isAttack ? ' run-button--risk' : ' run-button--safe'}`}
              type="button"
              onClick={() => onFire(selected, instruction)}
              disabled={running || !instruction.trim()}
            >
              <span className="run-button-icon" aria-hidden="true">{running ? '◌' : isAttack ? '↗' : '▶'}</span>
              {running ? 'Running scenario…' : 'Run scenario'}
            </button>
          </div>
          <p className="scenario-note" aria-live="polite">
            {running ? 'Both agents are processing the same instruction.' : 'Both agents receive the same scenario for a fair comparison.'}
          </p>
        </div>
      </div>
    </div>
  );
}
