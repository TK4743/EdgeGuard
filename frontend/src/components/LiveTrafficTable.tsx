import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { PredictionResult } from '../types';
import { formatDataHex } from '../utils/incident';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface LiveTrafficTableProps {
  events: PredictionResult[];
}

export default function LiveTrafficTable({ events }: LiveTrafficTableProps) {
  return (
    <footer className="h-56 shrink-0 bg-[#f8f9fa] border-t border-[#dee2e6] flex flex-col overflow-hidden">
      <div className="px-4 py-2 bg-[#e9ecef] border-b border-[#dee2e6] text-[10px] text-[#495057] font-bold tracking-wider">
        LIVE CAN BUS TRAFFIC STREAM
      </div>
      <div className="flex-1 overflow-auto p-2 custom-scrollbar">
        <table className="gov-table w-full">
          <thead className="sticky top-0 z-10 bg-[#e9ecef]">
            <tr>
              <th className="w-24">Timestamp</th>
              <th className="w-16">CAN ID</th>
              <th className="w-12 text-center">DLC</th>
              <th>Payload (Hex)</th>
              <th className="w-24 text-center">Latency</th>
              <th className="w-28 text-center">Prediction</th>
            </tr>
          </thead>
          <tbody>
            {events.map((e, idx) => (
              <tr key={`${e.message.timestamp}-${e.message.canId}-${idx}`} className="hover:bg-[#e9ecef]">
                <td className="font-mono text-[10px] text-slate-600">{e.message.timestamp.toFixed(4)}</td>
                <td className="font-mono font-bold text-[#1E3A5F]">{e.message.canId}</td>
                <td className="font-mono text-center">{e.message.dlc}</td>
                <td className="font-mono tracking-widest text-slate-700">{formatDataHex(e.message.data)}</td>
                <td className="font-mono text-center text-slate-600">{e.latencyMs.toFixed(2)} ms</td>
                <td className="text-center">
                  <span className={cn(
                    "px-1.5 py-0.5 text-[9px] font-bold rounded",
                    e.predictionLabel !== 0 ? "bg-red-100 text-red-700 border border-red-200" : "bg-green-100 text-green-700 border border-green-200"
                  )}>
                    {e.predictionClass}
                  </span>
                </td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center py-8 text-slate-500 font-semibold">
                  Waiting for CAN bus stream...
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </footer>
  );
}
