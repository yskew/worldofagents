import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import AttestationStatus from './AttestationStatus';
import type { AttestStep } from '../lib/api';

describe('AttestationStatus', () => {
  it('shows idle state with no history', () => {
    render(<AttestationStatus history={[]} />);
    expect(screen.getByTestId('attest-idle')).toBeInTheDocument();
  });

  it('reflects the latest window status (ok)', () => {
    const history: AttestStep[] = [
      { window_similarity: 1.0, cusum: 0, status: 'ok', windows: 1 },
    ];
    render(<AttestationStatus history={history} />);
    expect(screen.getByTestId('attest-current')).toHaveTextContent('OK');
  });

  it('shows an alarm on sustained drift', () => {
    const history: AttestStep[] = [
      { window_similarity: 0.2, cusum: 0.3, status: 'warning', windows: 1 },
      { window_similarity: 0.15, cusum: 0.65, status: 'alarm', windows: 2 },
    ];
    render(<AttestationStatus history={history} />);
    expect(screen.getByTestId('attest-current')).toHaveTextContent('ALARM');
    expect(screen.getByText('0.65')).toBeInTheDocument();
  });
});
