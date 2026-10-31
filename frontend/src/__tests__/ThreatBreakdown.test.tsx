import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import ThreatBreakdown from '../components/ThreatBreakdown';
import type { ThreatSummary } from '../types';

describe('ThreatBreakdown component', () => {
  it('renders threat breakdown categories with summary counts', () => {
    const summary: ThreatSummary = {
      dos: 15,
      fuzzy: 8,
      spoofing: 5,
    };

    render(<ThreatBreakdown summary={summary} />);

    expect(screen.getByText('Threat Breakdown')).toBeInTheDocument();
    expect(screen.getByText('DoS Attacks')).toBeInTheDocument();
    expect(screen.getByText('15')).toBeInTheDocument();
    expect(screen.getByText('Fuzzy Anomalies')).toBeInTheDocument();
    expect(screen.getByText('8')).toBeInTheDocument();
    expect(screen.getByText('Spoofing Attempts')).toBeInTheDocument();
    expect(screen.getByText('5')).toBeInTheDocument();
  });

  it('renders EdgeGuard model performance metrics', () => {
    const summary: ThreatSummary = { dos: 0, fuzzy: 0, spoofing: 0 };
    render(<ThreatBreakdown summary={summary} />);

    expect(screen.getByText('Model Info (EdgeGuard)')).toBeInTheDocument();
    expect(screen.getByText('70.08%')).toBeInTheDocument();
    expect(screen.getByText('75.85%')).toBeInTheDocument();
    expect(screen.getByText('0.9679')).toBeInTheDocument();
    expect(screen.getByText('0.7011')).toBeInTheDocument();
  });
});
