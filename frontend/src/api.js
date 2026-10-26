const BASE = '';

export async function fetchAttacks() {
  const r = await fetch(`${BASE}/attacks`);
  return r.json();
}

export async function runAttack(attackId, userInstruction) {
  const r = await fetch(`${BASE}/run-attack`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ attack_id: attackId, user_instruction: userInstruction }),
  });
  return r.json();
}

export async function fetchLedger() {
  const r = await fetch(`${BASE}/ledger`);
  return r.json();
}

export async function resetArena() {
  const r = await fetch(`${BASE}/reset`, { method: 'POST' });
  return r.json();
}

export function streamAgent(agent, onStep, onDone) {
  const es = new EventSource(`${BASE}/stream/${agent}`);
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data);
      if (data.type === 'done') { es.close(); onDone && onDone(); }
      else onStep(data);
    } catch {}
  };
  es.onerror = () => { es.close(); onDone && onDone(); };
  return () => es.close();
}
