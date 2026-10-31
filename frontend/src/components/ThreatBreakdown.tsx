import type { ThreatSummary } from '../types';

interface ThreatBreakdownProps {
  summary: ThreatSummary;
}

export default function ThreatBreakdown({ summary }: ThreatBreakdownProps) {
  const maxCategoryCount = Math.max(summary.dos, summary.fuzzy, summary.spoofing, 1);

  return (
    <aside className="w-80 xl:w-96 shrink-0 border-r border-[#dee2e6] bg-[#f8f9fa] flex flex-col overflow-y-auto custom-scrollbar p-4 gap-4">
      {/* THREAT BREAKDOWN PANEL */}
      <div className="gov-panel p-4">
        <h4 className="text-[10px] font-bold text-[#495057] tracking-wider mb-4 uppercase border-b border-[#dee2e6] pb-2">
          Threat Breakdown
        </h4>
        <div className="space-y-4">
          {/* DoS */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-semibold text-slate-800">DoS Attacks</span>
              <span className="font-mono font-bold text-slate-900">{summary.dos}</span>
            </div>
            <div className="w-full bg-slate-200 h-2.5 rounded-sm overflow-hidden">
              <div 
                className="bg-[#dc3545] h-full transition-all duration-300"
                style={{ width: `${(summary.dos / maxCategoryCount) * 100}%` }}
              />
            </div>
          </div>
          {/* Spoofing */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-semibold text-slate-800">Spoofing Attempts</span>
              <span className="font-mono font-bold text-slate-900">{summary.spoofing}</span>
            </div>
            <div className="w-full bg-slate-200 h-2.5 rounded-sm overflow-hidden">
              <div 
                className="bg-[#fd7e14] h-full transition-all duration-300"
                style={{ width: `${(summary.spoofing / maxCategoryCount) * 100}%` }}
              />
            </div>
          </div>
          {/* Fuzzy */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="font-semibold text-slate-800">Fuzzy Anomalies</span>
              <span className="font-mono font-bold text-slate-900">{summary.fuzzy}</span>
            </div>
            <div className="w-full bg-slate-200 h-2.5 rounded-sm overflow-hidden">
              <div 
                className="bg-[#ffc107] h-full transition-all duration-300"
                style={{ width: `${(summary.fuzzy / maxCategoryCount) * 100}%` }}
              />
            </div>
          </div>
        </div>
      </div>

      {/* MODEL INFO PANEL */}
      <div className="gov-panel p-4 flex-1">
        <h4 className="text-[10px] font-bold text-[#495057] tracking-wider mb-4 uppercase border-b border-[#dee2e6] pb-2">
          Model Info (EdgeGuard)
        </h4>
        
        <div className="space-y-3 text-[11px]">
          <div className="flex justify-between border-b border-dashed border-[#ced4da] pb-1">
            <span className="font-bold text-slate-700">Accuracy</span>
            <span className="font-mono font-bold text-[#1E3A5F]">70.08%</span>
          </div>
          <div className="flex justify-between border-b border-dashed border-[#ced4da] pb-1">
            <span className="font-bold text-slate-700">Macro F1</span>
            <span className="font-mono font-bold text-[#1E3A5F]">75.85%</span>
          </div>
          
          <div className="pt-2">
            <span className="font-bold text-slate-700 mb-1 block">Per-Class F1 Scores</span>
            <div className="grid grid-cols-2 gap-2 text-slate-600 font-mono text-[10px]">
              <div>Normal: <span className="font-bold text-[#198754]">0.9679</span></div>
              <div>DoS: <span className="font-bold text-[#dc3545]">0.7011</span></div>
              <div>Fuzzy: <span className="font-bold text-[#ffc107]">0.6288</span></div>
              <div>Spoofing: <span className="font-bold text-[#fd7e14]">0.7362</span></div>
            </div>
          </div>

          <div className="bg-[#e9ecef] p-2 rounded mt-3 text-[10px] text-slate-700 leading-tight">
            <span className="font-bold">Methodology:</span> Evaluated using a strict chronological split (not random) to avoid temporal leakage on the HCRL dataset.
          </div>

          <div className="bg-amber-100 border border-amber-300 text-amber-900 p-2 rounded mt-3 text-[10px] leading-tight font-semibold">
            *Known Limitations:* Attack-type sub-classification remains an active research challenge; binary attack detection (Normal vs Anomalous) achieves ~96% reliability.
          </div>
        </div>
      </div>
    </aside>
  );
}
