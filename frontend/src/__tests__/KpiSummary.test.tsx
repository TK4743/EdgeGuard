import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import KpiSummary from '../components/KpiSummary';

describe('KpiSummary component', () => {
  it('renders total messages, anomaly counts, latency, and connected status', () => {
    render(
      <KpiSummary
        totalPackets={125000}
        anomalyCount={42}
        lastLatency={0.456}
        connected={true}
      />
    );

    expect(screen.getByText('TOTAL MESSAGES')).toBeInTheDocument();
    expect(screen.getByText('125,000')).toBeInTheDocument();
    expect(screen.getByText('DETECTED ANOMALIES')).toBeInTheDocument();
    expect(screen.getByText('42')).toBeInTheDocument();
    expect(screen.getByText('0.46 ms')).toBeInTheDocument();
    expect(screen.getByText('CONNECTED')).toBeInTheDocument();
  });

  it('displays DISCONNECTED when connected is false', () => {
    render(
      <KpiSummary
        totalPackets={0}
        anomalyCount={0}
        lastLatency={0}
        connected={false}
      />
    );

    expect(screen.getByText('DISCONNECTED')).toBeInTheDocument();
    expect(screen.getAllByText('0')).toHaveLength(2);
    expect(screen.getByText('0.00 ms')).toBeInTheDocument();
  });
});
