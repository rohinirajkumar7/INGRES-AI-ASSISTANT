import React from 'react';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts';
import GeoMap from './GeoMap';

const ChartDisplay = ({ chart, onStateSelect }) => {
  if (!chart || !chart.type) return null;
  const { type, data, title } = chart;

  if (type === 'map') {
    return (
      <div className="chart-container">
        <h4>{title}</h4>
        <GeoMap tiles={data} metric={chart.metric} highlight={chart.highlight || []} onSelect={onStateSelect} />
      </div>
    );
  }

  if (!data || data.length === 0) return null;

  if (type === 'bar') {
    return (
      <div className="chart-container">
        <h4>{title}</h4>
        <ResponsiveContainer width="100%" height={Math.max(160, data.length * 38 + 40)}>
          <BarChart data={data} layout="vertical" margin={{ left: 8, right: 24 }}>
            <CartesianGrid strokeDasharray="3 3" horizontal={false} />
            <XAxis type="number" unit={chart.unit === '%' ? '%' : ''} />
            <YAxis type="category" dataKey="name" width={110} tick={{ fontSize: 12 }} />
            <Tooltip formatter={(v) => `${v} ${chart.unit || ''}`} />
            <Bar dataKey="value" name={chart.unit || 'value'} radius={[0, 6, 6, 0]}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color || '#0f766e'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === 'categories') {
    return (
      <div className="chart-container">
        <h4>{title}</h4>
        <ResponsiveContainer width="100%" height={240}>
          <PieChart>
            <Pie data={data} dataKey="value" nameKey="name" innerRadius={50} outerRadius={85} paddingAngle={2}
                 label={({ value }) => value}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color} />
              ))}
            </Pie>
            <Tooltip />
            <Legend />
          </PieChart>
        </ResponsiveContainer>
      </div>
    );
  }

  if (type === 'comparison') {
    return (
      <div className="chart-container">
        <h4>{title}</h4>
        <ResponsiveContainer width="100%" height={280}>
          <BarChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis yAxisId="left" orientation="left" stroke="#3b82f6" />
            <YAxis yAxisId="right" orientation="right" stroke="#0f766e" />
            <Tooltip />
            <Legend />
            <Bar yAxisId="left" dataKey="rainfall" fill="#3b82f6" name="Rainfall (mm)" radius={[6, 6, 0, 0]} />
            <Bar yAxisId="right" dataKey="extraction" name="Extraction stage (%)" radius={[6, 6, 0, 0]}>
              {data.map((entry) => (
                <Cell key={entry.name} fill={entry.color || '#0f766e'} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
    );
  }

  return null;
};

export default ChartDisplay;