import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import SignalsFeed from './SignalsFeed';
import type { SignalEvent } from '../lib/api';

const events: SignalEvent[] = [
  { jti: '1', type: 'behavioral-anomaly', subject: 'alice@example.com', agentName: 'coder', reason: 'verification_failed', score: 0.21 },
  { jti: '2', type: 'session-revoked', subject: 'bob@example.com', agentName: 'devops', reason: 'admin_revocation' },
];

describe('SignalsFeed', () => {
  it('renders risk events with labels and subjects', () => {
    render(<SignalsFeed events={events} />);
    expect(screen.getByTestId('signals-feed')).toBeInTheDocument();
    expect(screen.getByText('BEHAVIORAL ANOMALY')).toBeInTheDocument();
    expect(screen.getByText('SESSION REVOKED')).toBeInTheDocument();
    expect(screen.getByText(/alice@example.com/)).toBeInTheDocument();
    expect(screen.getByText('score 0.21')).toBeInTheDocument();
  });

  it('shows empty state', () => {
    render(<SignalsFeed events={[]} />);
    expect(screen.getByTestId('signals-empty')).toBeInTheDocument();
  });
});
