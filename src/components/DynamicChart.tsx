import React from 'react';
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, RadarChart, Radar, PolarGrid, PolarAngleAxis, PolarRadiusAxis,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface ChartProps {
  data: any;
}

export default function DynamicChart({ data }: ChartProps) {
  if (!data || !data.data || data.data.length === 0) {
    return null;
  }

  const keys = Object.keys(data.data[0]).filter(k => k !== data.xAxis && k !== 'Year' && k !== 'name');
  const colors = ['#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa'];

  // Choose chart based on requested type, default to area for "Supercomputer" feel
  const chartType = data.chartType || 'area';

  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="bg-slate-900/80 backdrop-blur-md border border-white/10 p-4 rounded-xl shadow-2xl">
          <p className="text-slate-300 font-bold mb-2">{`${label}`}</p>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="flex items-center space-x-2 text-sm my-1">
              <span className="w-3 h-3 rounded-full" style={{ backgroundColor: entry.color }}></span>
              <span className="text-slate-200">{entry.name}:</span>
              <span className="font-mono text-white font-semibold">{entry.value.toLocaleString()}</span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const renderChart = () => {
    switch (chartType) {
      case 'radar':
        return (
          <RadarChart cx="50%" cy="50%" outerRadius="80%" data={data.data}>
            <PolarGrid stroke="#ffffff20" />
            <PolarAngleAxis dataKey={data.xAxis || 'name'} tick={{ fill: '#94a3b8', fontSize: 12 }} />
            <PolarRadiusAxis angle={30} domain={[0, 'auto']} tick={{ fill: '#94a3b8' }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {keys.map((key, index) => (
              <Radar key={key} name={key} dataKey={key} stroke={colors[index % colors.length]} fill={colors[index % colors.length]} fillOpacity={0.5} />
            ))}
          </RadarChart>
        );
      case 'bar':
        return (
          <BarChart data={data.data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis dataKey={data.xAxis || 'Year'} stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} />
            <Tooltip content={<CustomTooltip />} cursor={{ fill: '#ffffff05' }} />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {keys.map((key, index) => (
              <Bar key={key} dataKey={key} fill={colors[index % colors.length]} radius={[4, 4, 0, 0]} barSize={24} />
            ))}
          </BarChart>
        );
      case 'area':
      default:
        return (
          <AreaChart data={data.data} margin={{ top: 20, right: 30, left: 0, bottom: 5 }}>
            <defs>
              {keys.map((key, index) => (
                <linearGradient key={`color${index}`} id={`color${index}`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={colors[index % colors.length]} stopOpacity={0.8} />
                  <stop offset="95%" stopColor={colors[index % colors.length]} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" vertical={false} />
            <XAxis dataKey={data.xAxis || 'Year'} stroke="#94a3b8" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
            <YAxis stroke="#94a3b8" tick={{ fontSize: 12 }} axisLine={false} tickLine={false} />
            <Tooltip content={<CustomTooltip />} />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {keys.map((key, index) => (
              <Area
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={3}
                fillOpacity={1}
                fill={`url(#color${index})`}
                activeDot={{ r: 6, strokeWidth: 0 }}
              />
            ))}
          </AreaChart>
        );
    }
  };

  return (
    <div className="w-full h-[400px] p-6 glass-card rounded-2xl bg-slate-900 border border-slate-700/50 relative overflow-hidden group shadow-[0_0_30px_rgba(99,102,241,0.05)] hover:shadow-[0_0_40px_rgba(99,102,241,0.15)] transition-shadow duration-500">
      {/* Decorative background glow */}
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-indigo-500/20 rounded-full blur-[100px] pointer-events-none transition-opacity duration-500 opacity-50 group-hover:opacity-100" />

      <div className="flex justify-between items-center mb-6 relative z-10">
        <h3 className="text-xl font-bold text-white tracking-tight">{data.title}</h3>
        <span className="text-xs bg-indigo-500/20 text-indigo-300 px-3 py-1 rounded-full uppercase tracking-widest font-semibold border border-indigo-500/30">
          Simulated
        </span>
      </div>

      <div className="h-[300px] relative z-10">
        <ResponsiveContainer width="100%" height="100%">
          {renderChart()}
        </ResponsiveContainer>
      </div>
    </div>
  );
}
