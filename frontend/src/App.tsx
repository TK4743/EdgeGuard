import { useState, useEffect, useRef } from 'react';
import { Client } from '@stomp/stompjs';
import Header from './components/Header';
import KpiSummary from './components/KpiSummary';
import ThreatBreakdown from './components/ThreatBreakdown';
import TrafficTimeline from './components/TrafficTimeline';
import IncidentRegister from './components/IncidentRegister';
import LiveTrafficTable from './components/LiveTrafficTable';
import type { PredictionResult, TimelinePoint, Incident, ThreatSummary } from './types';
import { generateIncidentId, getSeverity } from './utils/incident';

export default function App() {
  const [connected, setConnected] = useState(false);
  const [currentTime, setCurrentTime] = useState("-");
  
  // Dashboard State
  const [totalPackets, setTotalPackets] = useState(0);
  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [rawEvents, setRawEvents] = useState<PredictionResult[]>([]);
  const [timelineData, setTimelineData] = useState<TimelinePoint[]>([]);
  const [summary, setSummary] = useState<ThreatSummary>({ dos: 0, fuzzy: 0, spoofing: 0 });
  const [lastLatency, setLastLatency] = useState(0);
  
  // Ref for tracking timeline buckets — initialized immediately to prevent first-second packet drops
  const bucketRef = useRef<{ time: string; normal: number; attack: number }>({
    time: '',
    normal: 0,
    attack: 0,
  });

  useEffect(() => {
    const clock = setInterval(() => {
      const now = new Date();
      setCurrentTime(now.toLocaleTimeString('en-US', { hour12: false }));
    }, 1000);

    // Initialize 60s timeline buffer
    const initialTimeline: TimelinePoint[] = [];
    const now = new Date();
    for (let i = 60; i >= 0; i--) {
      const t = new Date(now.getTime() - i * 1000);
      initialTimeline.push({
        time: t.toLocaleTimeString('en-US', { hour12: false }),
        normal: 0,
        attack: 0,
      });
    }
    setTimelineData(initialTimeline);

    // Setup STOMP client over WebSocket
    const brokerURL = import.meta.env.VITE_WS_URL || 'ws://localhost:8080/ws/alerts';
    const client = new Client({
      brokerURL,
      reconnectDelay: 5000,
      onConnect: () => {
        setConnected(true);
        client.subscribe('/topic/alerts', (msg) => {
          try {
            const payload = JSON.parse(msg.body) as PredictionResult;
            handleNewData(payload);
          } catch (e) {
            console.error('Failed to parse STOMP alert payload:', e);
          }
        });
      },
      onDisconnect: () => {
        setConnected(false);
      },
      onWebSocketError: () => {
        setConnected(false);
      },
    });

    client.activate();

    return () => {
      client.deactivate();
      clearInterval(clock);
    };
  }, []);

  // Aggregation ticker for timeline
  useEffect(() => {
    const ticker = setInterval(() => {
      const now = new Date();
      const timeStr = now.toLocaleTimeString('en-US', { hour12: false });
      
      setTimelineData(prev => {
        const newArr = [...prev.slice(1)];
        newArr.push({ ...bucketRef.current, time: timeStr });
        return newArr;
      });
      
      // Reset bucket for next second
      bucketRef.current = { time: timeStr, normal: 0, attack: 0 };
    }, 1000);
    return () => clearInterval(ticker);
  }, []);

  const handleNewData = (payload: PredictionResult) => {
    setTotalPackets(prev => prev + 1);
    setLastLatency(payload.latencyMs);

    const isAttack = payload.predictionLabel !== 0;

    // Aggregate into current 1-second bucket
    if (isAttack) {
      bucketRef.current.attack++;
    } else {
      bucketRef.current.normal++;
    }

    if (isAttack) {
      // Deterministic stable incident identifier
      const incidentId = generateIncidentId(payload.message);
      const newIncident: Incident = {
        id: incidentId,
        timestamp: payload.message.timestamp,
        canId: payload.message.canId,
        classification: payload.predictionClass,
        severity: getSeverity(payload.predictionClass),
        raw: payload,
      };

      setIncidents(prev => {
        const next = [newIncident, ...prev];
        if (next.length > 50) return next.slice(0, 50);
        return next;
      });

      setSummary(prev => {
        const next = { ...prev };
        if (payload.predictionClass === 'DoS') next.dos++;
        else if (payload.predictionClass === 'Fuzzy') next.fuzzy++;
        else if (payload.predictionClass === 'Spoofing') next.spoofing++;
        return next;
      });
    }

    setRawEvents(prev => {
      const next = [payload, ...prev];
      if (next.length > 30) return next.slice(0, 30);
      return next;
    });
  };

  let statusText = "OPERATIONAL";
  let statusBg = "bg-[#198754] text-white";
  if (!connected) {
    statusText = "INACTIVE";
    statusBg = "bg-[#6c757d] text-white";
  } else {
    const recentAttacks = timelineData.slice(-10).reduce((sum, pt) => sum + pt.attack, 0);
    if (recentAttacks > 50) {
      statusText = "CRITICAL";
      statusBg = "bg-[#dc3545] text-white";
    } else if (recentAttacks > 10) {
      statusText = "ELEVATED";
      statusBg = "bg-[#fd7e14] text-white";
    }
  }

  const anomalyCount = summary.dos + summary.fuzzy + summary.spoofing;

  return (
    <div className="h-screen w-screen bg-[#f8f9fa] text-[#212529] flex flex-col overflow-hidden select-none font-sans">
      {/* 1. HEADER */}
      <Header
        connected={connected}
        statusText={statusText}
        statusBg={statusBg}
        currentTime={currentTime}
      />

      {/* 2. KPI STRIP */}
      <KpiSummary
        totalPackets={totalPackets}
        anomalyCount={anomalyCount}
        lastLatency={lastLatency}
        connected={connected}
      />

      {/* 3. MAIN BODY */}
      <div className="flex-1 flex overflow-hidden">
        {/* LEFT PANEL — THREAT BREAKDOWN & MODEL INFO */}
        <ThreatBreakdown summary={summary} />

        {/* CENTER PANEL — TIMELINE CHART */}
        <TrafficTimeline timelineData={timelineData} />

        {/* RIGHT PANEL — INCIDENT REGISTER */}
        <IncidentRegister incidents={incidents} />
      </div>

      {/* 4. BOTTOM PANEL — RAW PACKET TABLE */}
      <LiveTrafficTable events={rawEvents} />
    </div>
  );
}
