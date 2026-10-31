import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import IncidentRegister from '../components/IncidentRegister';
import type { Incident } from '../types';

describe('IncidentRegister component', () => {
  it('renders empty state when incidents array is empty', () => {
    render(<IncidentRegister incidents={[]} />);
    expect(screen.getByText('No anomalies detected.')).toBeInTheDocument();
  });

  it('renders incidents with stable, non-shifting IDs', () => {
    const incidentA: Incident = {
      id: 'INC-2026-0316-12345',
      timestamp: 1478198376.1234,
      canId: '0316',
      classification: 'DoS',
      severity: 'CRITICAL',
      raw: {
        message: { timestamp: 1478198376.1234, canId: '0316', dlc: 8, data: [], flag: 'R' },
        predictionLabel: 1,
        predictionClass: 'DoS',
        latencyMs: 0.42,
        anomalyScore: 0.89,
      },
    };

    const incidentB: Incident = {
      id: 'INC-2026-043F-54321',
      timestamp: 1478198378.5432,
      canId: '043F',
      classification: 'Spoofing',
      severity: 'HIGH',
      raw: {
        message: { timestamp: 1478198378.5432, canId: '043F', dlc: 8, data: [], flag: 'R' },
        predictionLabel: 3,
        predictionClass: 'Spoofing',
        latencyMs: 0.38,
        anomalyScore: 0.77,
      },
    };

    // First render with incident A only
    const { rerender } = render(<IncidentRegister incidents={[incidentA]} />);
    expect(screen.getByText('INC-2026-0316-12345')).toBeInTheDocument();

    // Now prepend new incident B to list (simulating new alert received)
    rerender(<IncidentRegister incidents={[incidentB, incidentA]} />);

    // CRITICAL FIX VERIFICATION: incident A must retain its original ID and not shift
    expect(screen.getByText('INC-2026-0316-12345')).toBeInTheDocument();
    expect(screen.getByText('INC-2026-043F-54321')).toBeInTheDocument();
    expect(screen.getByText('DoS')).toBeInTheDocument();
    expect(screen.getByText('Spoofing')).toBeInTheDocument();
  });
});
