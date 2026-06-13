import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import '@testing-library/jest-dom';
import TelemetryPanel from './TelemetryPanel';
import type { TelemetrySummary } from '../lib/api';

const summary: TelemetrySummary = {
  tool_histogram: { search: 0.6, read_file: 0.4 },
  unique_tools: 2,
  sequence_length: 5,
  tool_call_ratio: 0.8,
  error_rate: 0.25,
  mean_interval_s: 1.5,
};

describe('TelemetryPanel', () => {
  it('renders the extracted patterns', () => {
    render(
      <TelemetryPanel summary={summary} source="otel" ingestedSpans={5} mappedSteps={5} applied={true} />,
    );
    expect(screen.getByTestId('telemetry-panel')).toBeInTheDocument();
    expect(screen.getByText('PATTERNS // OTEL')).toBeInTheDocument();
    expect(screen.getByText('search')).toBeInTheDocument();
    expect(screen.getByText('read_file')).toBeInTheDocument();
    expect(screen.getByText('25.0%')).toBeInTheDocument(); // error rate
    expect(screen.getByText('1.5s')).toBeInTheDocument(); // mean interval
    expect(screen.getByText('SIGNATURE ENRICHED')).toBeInTheDocument();
  });

  it('shows preview state when not applied', () => {
    render(
      <TelemetryPanel summary={summary} source="langfuse" ingestedSpans={3} mappedSteps={3} applied={false} />,
    );
    expect(screen.getByText('PREVIEW ONLY')).toBeInTheDocument();
  });

  it('handles a trace with no tool calls', () => {
    const empty: TelemetrySummary = { ...summary, tool_histogram: {}, unique_tools: 0 };
    render(
      <TelemetryPanel summary={empty} source="braintrust" ingestedSpans={1} mappedSteps={1} applied={false} />,
    );
    expect(screen.getByText('no tool calls in trace')).toBeInTheDocument();
  });
});
