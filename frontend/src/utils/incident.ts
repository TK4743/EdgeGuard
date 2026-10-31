import type { CanMessage, SeverityLevel } from '../types';

export function generateIncidentId(message: CanMessage): string {
  const tsPart = Math.floor((message.timestamp || 0) * 1000) % 100000;
  const canPart = (message.canId || '0000').toUpperCase();
  return `INC-2026-${canPart}-${tsPart.toString().padStart(5, '0')}`;
}

export function getSeverity(label: string): SeverityLevel {
  if (label === 'DoS') return 'CRITICAL';
  if (label === 'Spoofing') return 'HIGH';
  if (label === 'Fuzzy') return 'MEDIUM';
  return 'LOW';
}

export function formatDataHex(dataArr: string[] | undefined | null): string {
  if (!dataArr || !Array.isArray(dataArr)) return "";
  return dataArr.map(d => d.toString().padStart(2, '0').toUpperCase()).join(' ');
}
