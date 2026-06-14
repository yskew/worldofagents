import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import McpResult from './McpResult';
import type { McpCallResult } from '../lib/api';

const allowed: McpCallResult = {
  tool: 'edit_file',
  status: 'executed',
  result: { echo: { path: 'x.py' } },
  agent_id: 'abcd1234-aaaa',
  principal: 'demo_user_001',
};

describe('McpResult', () => {
  it('renders an allowed execution', () => {
    render(<McpResult result={allowed} />);
    expect(screen.getByTestId('mcp-allowed')).toBeInTheDocument();
    expect(screen.getByText(/EXECUTED: edit_file/)).toBeInTheDocument();
    expect(screen.getByText(/demo_user_001/)).toBeInTheDocument();
  });

  it('renders a denial', () => {
    render(<McpResult error="tool_not_authorized: deploy" />);
    expect(screen.getByTestId('mcp-denied')).toBeInTheDocument();
    expect(screen.getByText(/tool_not_authorized/)).toBeInTheDocument();
  });

  it('renders empty state', () => {
    render(<McpResult />);
    expect(screen.getByText(/call a tool to see/)).toBeInTheDocument();
  });
});
