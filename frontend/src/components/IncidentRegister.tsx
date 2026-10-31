import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Incident } from '../types';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface IncidentRegisterProps {
  incidents: Incident[];
}

export default function IncidentRegister({ incidents }: IncidentRegisterProps) {
  return (
    <aside className="w-80 xl:w-[450px] shrink-0 bg-[#f8f9fa] flex flex-col overflow-hidden">
      <div className="px-4 py-2 bg-[#e9ecef] border-b border-[#dee2e6] text-[10px] text-[#495057] font-bold tracking-wider">
        ANOMALY LOG (LATEST 50)
      </div>
      
      <div className="flex-1 overflow-auto custom-scrollbar p-2">
        <table className="gov-table">
          <thead>
            <tr>
              <th>INCIDENT ID</th>
              <th>TIMESTAMP</th>
              <th>CAN ID</th>
              <th>CLASSIFICATION</th>
            </tr>
          </thead>
          <tbody>
            {incidents.length === 0 ? (
              <tr>
                <td colSpan={4} className="text-center py-4 text-slate-500 font-semibold text-xs">
                  No anomalies detected.
                </td>
              </tr>
            ) : incidents.map((incident) => (
              <tr key={incident.id}>
                <td className="font-mono text-[#1E3A5F]">{incident.id}</td>
                <td className="font-mono text-[10px]">{incident.timestamp.toFixed(4)}</td>
                <td className="font-mono font-bold text-slate-800">{incident.canId}</td>
                <td>
                  <span className={cn(
                    incident.severity === 'CRITICAL' ? "badge-critical" :
                    incident.severity === 'HIGH' ? "badge-high" :
                    incident.severity === 'MEDIUM' ? "badge-medium" :
                    "badge-low"
                  )}>
                    {incident.classification}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </aside>
  );
}
