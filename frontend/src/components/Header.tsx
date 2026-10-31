import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

interface HeaderProps {
  connected: boolean;
  statusText: string;
  statusBg: string;
  currentTime: string;
}

export default function Header({
  statusText,
  statusBg,
  currentTime,
}: HeaderProps) {
  return (
    <header className="h-14 shrink-0 bg-[#1E3A5F] text-white border-b border-[#13243a] px-6 flex items-center justify-between z-10">
      <div className="flex items-center gap-4">
        {/* Mandatory Logo Container Slot */}
        <div id="app-logo-slot" className="logo-container" aria-label="Company Logo Slot"></div>
        
        <h1 className="text-sm font-bold tracking-wider uppercase">
          National Cyber Security Monitoring Centre
        </h1>
        <span className="px-2 py-0.5 rounded bg-amber-500/20 text-amber-400 border border-amber-500/50 text-[10px] font-mono font-bold">
          OFFLINE MODE (EDGE AI)
        </span>
        <span className="px-2 py-0.5 rounded bg-white/10 text-white/80 text-[10px] font-mono font-bold">
          NODE: VE-CAN-01
        </span>
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-slate-300">SYSTEM STATUS:</span>
          <span className={cn("px-2.5 py-0.5 text-[10px] font-extrabold rounded tracking-wider", statusBg)}>
            {statusText}
          </span>
        </div>
        <div className="h-8 w-px bg-white/20"></div>
        <div className="flex flex-col items-end font-mono text-[10px]">
          <span className="text-[8px] text-slate-400 font-sans">CURRENT TIME</span>
          <span className="font-bold text-[#20c997]">{currentTime}</span>
        </div>
      </div>
    </header>
  );
}
