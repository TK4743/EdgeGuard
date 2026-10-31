import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import LiveTrafficTable from '../components/LiveTrafficTable';
import type { PredictionResult } from '../types';

describe('LiveTrafficTable component', () => {
  it('renders waiting state when no events exist', () => {
    render(<LiveTrafficTable events={[]} />);
    expect(screen.getByText('Waiting for CAN bus stream...')).toBeInTheDocument();
  });

  it('renders CAN frame rows with uppercase padded hex payloads', () => {
    const events: PredictionResult[] = [
      {
        message: {
          timestamp: 1478198376.1234,
          canId: '0316',
          dlc: 8,
          data: ['5', '21', '68', '9', '21', '21', '0', '6e'],
          flag: 'R',
        },
        predictionLabel: 1,
        predictionClass: 'DoS',
        latencyMs: 0.428,
        anomalyScore: 0.892,
      },
    ];

    render(<LiveTrafficTable events={events} />);

    expect(screen.getByText('0316')).toBeInTheDocument();
    expect(screen.getByText('05 21 68 09 21 21 00 6E')).toBeInTheDocument();
    expect(screen.getByText('0.43 ms')).toBeInTheDocument();
    expect(screen.getByText('DoS')).toBeInTheDocument();
  });
});
