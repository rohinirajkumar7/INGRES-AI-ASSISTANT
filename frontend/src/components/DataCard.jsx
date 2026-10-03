import React from 'react';
import { CATEGORY_COLORS, formatNumber } from '../utils';

const Item = ({ label, value, unit }) => {
  if (value === null || value === undefined) return null;
  return (
    <div className="data-item">
      <span className="data-label">{label}</span>
      <span className="data-value">{formatNumber(value, unit === 'mm' || unit === '%' ? 1 : 0)} {unit}</span>
    </div>
  );
};

const DataCard = ({ data }) => (
  <div className="data-card">
    <div className="card-header">
      <div>
        <h3>{data.name}</h3>
        <span className="state-badge">{data.subtitle}</span>
      </div>
      {data.category && (
        <span className="category-pill" style={{ background: CATEGORY_COLORS[data.category] }}>
          {data.category_label}
        </span>
      )}
    </div>
    <div className="card-body">
      <Item label="💧 Rainfall" value={data.rainfall} unit="mm" />
      <Item label="📊 Extraction stage" value={data.extraction_stage} unit="%" />
      <Item label="♻️ Recharge" value={data.gw_recharge} unit="ham" />
      <Item label="💦 Net availability" value={data.net_availability} unit="ham" />
    </div>
  </div>
);

export default DataCard;
