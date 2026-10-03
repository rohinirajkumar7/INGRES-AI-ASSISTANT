import React from 'react';
import { CATEGORY_COLORS, CATEGORY_LABELS, formatNumber, rainfallColor } from '../utils';

// Tile-grid "cartogram" of India: one tile per state/UT, positioned roughly
// where it sits on the map. Works offline and needs no GeoJSON.
const TileMap = ({ tiles, metric = 'stage', highlight = [], onSelect }) => {
  if (!tiles || tiles.length === 0) return null;
  const cols = Math.max(...tiles.map((t) => t.col)) + 1;

  return (
    <div className="tilemap-wrap">
      <div className="tilemap" style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}>
        {tiles.map((t) => {
          const color = metric === 'rainfall' ? rainfallColor(t.rainfall) : CATEGORY_COLORS[t.category];
          const dark = metric === 'rainfall' ? (t.rainfall || 0) > 1400 : t.category !== 'semi_critical' && t.category !== 'no_data';
          const label = metric === 'rainfall'
            ? `${formatNumber(t.rainfall, 0)} mm`
            : `${formatNumber(t.stage, 1)}% - ${CATEGORY_LABELS[t.category]}`;
          return (
            <button
              key={t.state}
              type="button"
              className={`tile ${highlight.includes(t.state) ? 'tile-highlight' : ''}`}
              style={{ gridRow: t.row + 1, gridColumn: t.col + 1, background: color, color: dark ? '#fff' : '#1f2937' }}
              title={`${t.state}: ${label}`}
              aria-label={`${t.state}: ${label}`}
              onClick={() => onSelect && onSelect(t.state)}
            >
              {t.code}
            </button>
          );
        })}
      </div>
      <div className="legend">
        {metric === 'rainfall' ? (
          <span className="legend-item">Lighter = drier, darker = wetter (average rainfall)</span>
        ) : (
          Object.keys(CATEGORY_LABELS).map((key) => (
            <span className="legend-item" key={key}>
              <i className="legend-dot" style={{ background: CATEGORY_COLORS[key] }} />
              {CATEGORY_LABELS[key]}
            </span>
          ))
        )}
      </div>
    </div>
  );
};

export default TileMap;
