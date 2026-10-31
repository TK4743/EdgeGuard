import { describe, it, expect } from 'vitest';
import { generateIncidentId, getSeverity, formatDataHex } from '../utils/incident';
import type { CanMessage } from '../types';

describe('incident utilities', () => {
  it('generates deterministic incident ID for identical CAN message', () => {
    const msg: CanMessage = {
      timestamp: 1478198376.123,
      canId: '0316',
      dlc: 8,
      data: ['05', '21', '68', '09', '21', '21', '00', '6e'],
      flag: 'R',
    };

    const id1 = generateIncidentId(msg);
    const id2 = generateIncidentId(msg);
    expect(id1).toBe(id2);
    expect(id1).toMatch(/^INC-2026-0316-\d{5}$/);
  });

  it('generates distinct IDs for different timestamps or canIds', () => {
    const msg1: CanMessage = {
      timestamp: 1478198376.100,
      canId: '0316',
      dlc: 8,
      data: [],
      flag: 'R',
    };
    const msg2: CanMessage = {
      timestamp: 1478198376.200,
      canId: '0316',
      dlc: 8,
      data: [],
      flag: 'R',
    };
    const msg3: CanMessage = {
      timestamp: 1478198376.100,
      canId: '043F',
      dlc: 8,
      data: [],
      flag: 'R',
    };

    expect(generateIncidentId(msg1)).not.toBe(generateIncidentId(msg2));
    expect(generateIncidentId(msg1)).not.toBe(generateIncidentId(msg3));
  });

  it('maps prediction labels to expected severity levels', () => {
    expect(getSeverity('DoS')).toBe('CRITICAL');
    expect(getSeverity('Spoofing')).toBe('HIGH');
    expect(getSeverity('Fuzzy')).toBe('MEDIUM');
    expect(getSeverity('Normal')).toBe('LOW');
    expect(getSeverity('Unknown')).toBe('LOW');
  });

  it('formats payload hex arrays with uppercase padding', () => {
    expect(formatDataHex(['5', 'a', 'ff', '0'])).toBe('05 0A FF 00');
    expect(formatDataHex([])).toBe('');
    expect(formatDataHex(null)).toBe('');
    expect(formatDataHex(undefined)).toBe('');
  });
});
