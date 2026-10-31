import { describe, it, expect } from 'vitest';
import type { PredictionResult, ThreatSummary, Incident } from '../types';
import { generateIncidentId, getSeverity } from '../utils/incident';

describe('alert processing and state aggregation logic', () => {
  it('correctly aggregates threat summaries across different attack classifications', () => {
    const summary: ThreatSummary = { dos: 0, fuzzy: 0, spoofing: 0 };

    const payloads: PredictionResult[] = [
      {
        message: { timestamp: 1.0, canId: '0316', dlc: 8, data: [], flag: 'R' },
        predictionLabel: 1,
        predictionClass: 'DoS',
        latencyMs: 0.35,
        anomalyScore: 0.95,
      },
      {
        message: { timestamp: 1.1, canId: '043F', dlc: 8, data: [], flag: 'R' },
        predictionLabel: 3,
        predictionClass: 'Spoofing',
        latencyMs: 0.40,
        anomalyScore: 0.88,
      },
      {
        message: { timestamp: 1.2, canId: '02C0', dlc: 8, data: [], flag: 'R' },
        predictionLabel: 2,
        predictionClass: 'Fuzzy',
        latencyMs: 0.32,
        anomalyScore: 0.72,
      },
      {
        message: { timestamp: 1.3, canId: '018F', dlc: 8, data: [], flag: 'R' },
        predictionLabel: 0,
        predictionClass: 'Normal',
        latencyMs: 0.28,
        anomalyScore: 0.05,
      },
    ];

    const incidents: Incident[] = [];

    payloads.forEach((payload) => {
      const isAttack = payload.predictionLabel !== 0;
      if (isAttack) {
        if (payload.predictionClass === 'DoS') summary.dos++;
        else if (payload.predictionClass === 'Fuzzy') summary.fuzzy++;
        else if (payload.predictionClass === 'Spoofing') summary.spoofing++;

        incidents.unshift({
          id: generateIncidentId(payload.message),
          timestamp: payload.message.timestamp,
          canId: payload.message.canId,
          classification: payload.predictionClass,
          severity: getSeverity(payload.predictionClass),
          raw: payload,
        });
      }
    });

    expect(summary.dos).toBe(1);
    expect(summary.spoofing).toBe(1);
    expect(summary.fuzzy).toBe(1);
    expect(incidents.length).toBe(3);
    expect(incidents[0].classification).toBe('Fuzzy');
    expect(incidents[1].classification).toBe('Spoofing');
    expect(incidents[2].classification).toBe('DoS');
  });

  it('determines system severity status based on recent attack window', () => {
    const computeStatus = (connected: boolean, recentAttacks: number) => {
      if (!connected) return { text: 'INACTIVE', bg: 'bg-[#6c757d]' };
      if (recentAttacks > 50) return { text: 'CRITICAL', bg: 'bg-[#dc3545]' };
      if (recentAttacks > 10) return { text: 'ELEVATED', bg: 'bg-[#fd7e14]' };
      return { text: 'OPERATIONAL', bg: 'bg-[#198754]' };
    };

    expect(computeStatus(false, 0).text).toBe('INACTIVE');
    expect(computeStatus(true, 5).text).toBe('OPERATIONAL');
    expect(computeStatus(true, 15).text).toBe('ELEVATED');
    expect(computeStatus(true, 60).text).toBe('CRITICAL');
  });
});
