import React from 'react';

export default function TransactionLedger({ transactions }) {
  return (
    <div className="ledger-card">
      <div className="ledger-header">
        <div><span className="section-kicker">03 / PAYMENT RECORD</span><h2>Transaction ledger</h2><p>Every simulated transfer, in one place.</p></div>
        <span className="ledger-count"><span className="ledger-count-dot" />{transactions.length} {transactions.length === 1 ? 'ENTRY' : 'ENTRIES'}</span>
      </div>
      {transactions.length === 0 ? (
        <div className="ledger-empty"><span className="ledger-empty-mark" aria-hidden="true">↗</span><div><strong>No transactions yet</strong><p>Run a scenario to see its payment activity here.</p></div></div>
      ) : (
        <div className="ledger-table-wrap">
          <table className="ledger-table">
            <thead><tr><th scope="col">Transaction</th><th scope="col">Vendor</th><th scope="col">Destination</th><th scope="col">Amount</th><th scope="col">Outcome</th></tr></thead>
            <tbody>
              {transactions.map((transaction, index) => {
                const account = transaction.account_number || '';
                const isAttack = account.includes('9999') || account.includes('8888') || account.includes('ATTACK');
                return (
                  <tr className={isAttack ? 'ledger-row ledger-row--risk' : 'ledger-row'} key={transaction.transaction_id || `${transaction.vendor_id}-${index}`}>
                    <td><span className="transaction-id">{transaction.transaction_id?.slice(0, 14) || '—'}</span></td>
                    <td>{transaction.vendor_id || '—'}</td>
                    <td className={isAttack ? 'destination destination--risk' : 'destination'}>{account || '—'}</td>
                    <td className="transaction-amount">₹{Number(transaction.amount).toLocaleString('en-IN')}</td>
                    <td><span className={`transaction-status${isAttack ? ' transaction-status--risk' : ''}`}><span />{isAttack ? 'Flagged' : 'Approved'}</span></td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
