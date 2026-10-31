import { XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, AreaChart, Area } from 'recharts';
import type { TimelinePoint } from '../types';

interface TrafficTimelineProps {
  timelineData: TimelinePoint[];
}

export default function TrafficTimeline({ timelineData }: TrafficTimelineProps) {
  return (
    <main className="flex-1 flex flex-col bg-white overflow-hidden border-r border-[#dee2e6]">
      <div className="px-4 py-2 bg-[#e9ecef] border-b border-[#dee2e6] text-[10px] text-[#495057] font-bold tracking-wider shrink-0 flex justify-between">
        <span>TRAFFIC & THREAT TIMELINE (60s)</span>
      </div>
      
      <div className="flex-1 p-4">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={timelineData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="colorNormal" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#198754" stopOpacity={0.3}/>
                <stop offset="95%" stopColor="#198754" stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="colorAttack" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#dc3545" stopOpacity={0.5}/>
                <stop offset="95%" stopColor="#dc3545" stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#dee2e6" />
            <XAxis dataKey="time" minTickGap={30} tick={{fontSize: 10, fill: '#6c757d'}} tickMargin={10} />
            <YAxis tick={{fontSize: 10, fill: '#6c757d'}} tickFormatter={(val) => Math.round(val).toString()} />
            <Tooltip 
              contentStyle={{ backgroundColor: '#212529', border: 'none', borderRadius: '3px', fontSize: '11px', color: '#fff' }}
              itemStyle={{ color: '#fff' }}
            />
            <Area type="monotone" dataKey="normal" stroke="#198754" fillOpacity={1} fill="url(#colorNormal)" isAnimationActive={false} name="Normal Msgs/s" />
            <Area type="stepAfter" dataKey="attack" stroke="#dc3545" fillOpacity={1} fill="url(#colorAttack)" isAnimationActive={false} name="Attack Msgs/s" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </main>
  );
}
