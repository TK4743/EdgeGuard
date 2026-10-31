export interface CanMessage {
  timestamp: number;
  canId: string;
  dlc: number;
  data: string[];
  flag: string;
}

export interface PredictionResult {
  message: CanMessage;
  predictionLabel: number;
  predictionClass: string;
  latencyMs: number;
  anomalyScore: number;
}

export type SeverityLevel = 'CRITICAL' | 'HIGH' | 'MEDIUM' | 'LOW';

export interface Incident {
  id: string;
  timestamp: number;
  canId: string;
  classification: string;
  severity: SeverityLevel;
  raw: PredictionResult;
}

export interface TimelinePoint {
  time: string;
  normal: number;
  attack: number;
}

export interface ThreatSummary {
  dos: number;
  fuzzy: number;
  spoofing: number;
}
