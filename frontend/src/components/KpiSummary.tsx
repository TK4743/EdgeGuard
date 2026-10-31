import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface KpiSummaryProps {
  totalPackets: number;
  anomalyCount: number;
  lastLatency: number;
  connected: boolean;
}

export default function KpiSummary({
  totalPackets,
  anomalyCount,
  lastLatency,
  connected,
}: KpiSummaryProps) {
  return (
    <section className="h-16 shrink-0 bg-white border-b border-[#dee2e6] grid grid-cols-4 divide-x divide-[#dee2e6] px-6 py-2 shadow-sm z-0">
      <div className="flex items-center justify-between px-6">
        <span className="text-[10px] text-[#495057] font-bold tracking-wider">TOTAL MESSAGES</span>
        <span className="text-lg font-bold font-mono text-[#1E3A5F]">{totalPackets.toLocaleString()}</span>
      </div>
      <div className="flex items-center justify-between px-6">
        <span className="text-[10px] text-[#495057] font-bold tracking-wider">DETECTED ANOMALIES</span>
        <span className={cn("text-lg font-bold font-mono", anomalyCount > 0 ? "text-[#dc3545]" : "text-[#198754]")}>
          {anomalyCount}
        </span>
      </div>
      <div className="flex items-center justify-between px-6">
        <span className="text-[10px] text-[#495057] font-bold tracking-wider">LATEST LATENCY</span>
        <span className="text-lg font-bold font-mono text-[#1E3A5F]">{lastLatency.toFixed(2)} ms</span>
      </div>
      <div className="flex items-center justify-between px-6">
        <span className="text-[10px] text-[#495057] font-bold tracking-wider">STREAM STATUS</span>
        <span className={cn("text-base font-bold font-mono", connected ? "text-[#198754]" : "text-[#dc3545]")}>
          {connected ? "CONNECTED" : "DISCONNECTED"}
        </span>
      </div>
    </section>
  );
}
