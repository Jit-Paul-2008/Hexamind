import React from 'react';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer
} from 'recharts';

interface ChartProps {
  data: any;
}

export default function DynamicChart({ data }: ChartProps) {
  if (!data || !data.data || data.data.length === 0) {
    return null;
  }

  // Extract all keys from the first data object, ignoring the xAxis key
  const keys = Object.keys(data.data[0]).filter(k => k !== data.xAxis && k !== 'Year' && k !== 'name');
  
  // Define some nice colors for the lines/bars
  const colors = ['#818cf8', '#34d399', '#f472b6', '#fbbf24', '#60a5fa'];

  return (
    <div className="w-full h-[400px] my-8 p-6 glass-card rounded-2xl border border-indigo-500/20 bg-slate-900/50">
      <h3 className="text-xl font-bold mb-6 text-center text-indigo-300">{data.title}</h3>
      <ResponsiveContainer width="100%" height="100%">
        {data.chartType === 'line' ? (
          <LineChart data={data.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis dataKey={data.xAxis || 'Year'} stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc' }}
              itemStyle={{ color: '#e2e8f0' }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {keys.map((key, index) => (
              <Line
                key={key}
                type="monotone"
                dataKey={key}
                stroke={colors[index % colors.length]}
                strokeWidth={3}
                activeDot={{ r: 8 }}
              />
            ))}
          </LineChart>
        ) : (
          <BarChart data={data.data} margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#ffffff10" />
            <XAxis dataKey={data.xAxis || 'Year'} stroke="#94a3b8" />
            <YAxis stroke="#94a3b8" />
            <Tooltip
              contentStyle={{ backgroundColor: '#1e293b', border: '1px solid #334155', borderRadius: '8px', color: '#f8fafc' }}
              cursor={{ fill: '#ffffff10' }}
            />
            <Legend wrapperStyle={{ paddingTop: '20px' }} />
            {keys.map((key, index) => (
              <Bar key={key} dataKey={key} fill={colors[index % colors.length]} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        )}
      </ResponsiveContainer>
    </div>
  );
}
