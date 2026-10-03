import React, { useEffect, useMemo, useState } from 'react';
import { CATEGORY_COLORS, CATEGORY_LABELS, formatNumber, rainfallColor } from '../utils';
import TileMap from './TileMap';

// GeoJSON feature name -> state name(s) used in the dataset.
// Only the merged UT differs; every other name matches exactly.
const NAME_MAP = {
  'Dadra and Nagar Haveli and Daman and Diu': ['Dadra and Nagar Haveli', 'Daman and Diu'],
};

const W = 600;
const PAD = 8;
const SMALL_AREA_KM2 = 4000; // small UTs/states also get a clickable dot

let geoPromise = null; // fetch the file once per page load
const loadGeo = () => {
  if (!geoPromise) {
    geoPromise = fetch(`${process.env.PUBLIC_URL || ''}/india-states.geojson`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .catch((e) => {
        geoPromise = null; // allow a retry next time
        throw e;
      });
  }
  return geoPromise;
};

// Web Mercator, no dependencies.
const mercY = (lat) => Math.log(Math.tan(Math.PI / 4 + (lat * Math.PI) / 360));
const project = ([lon, lat]) => [(lon * Math.PI) / 180, mercY(lat)]; // both axes in radians

const ringsOf = (geom) => {
  if (!geom) return [];
  if (geom.type === 'Polygon') return [geom.coordinates];
  if (geom.type === 'MultiPolygon') return geom.coordinates;
  return [];
};

function buildShapes(geo) {
  let minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
  const feats = geo.features.map((f) => {
    const polys = ringsOf(f.geometry).map((poly) =>
      poly.map((ring) =>
        ring.map((pt) => {
          const p = project(pt);
          if (p[0] < minX) minX = p[0];
          if (p[0] > maxX) maxX = p[0];
          if (p[1] < minY) minY = p[1];
          if (p[1] > maxY) maxY = p[1];
          return p;
        })
      )
    );
    return { name: f.properties.name, area: f.properties.area_km2 || 0, polys };
  });
  const scale = (W - 2 * PAD) / (maxX - minX);
  const H = Math.round((maxY - minY) * scale + 2 * PAD);
  const tx = (x) => ((x - minX) * scale + PAD).toFixed(1);
  const ty = (y) => ((maxY - y) * scale + PAD).toFixed(1);

  const shapes = feats.map((f) => {
    let d = '';
    let best = null; // centroid of the biggest ring, for the small-state dot
    f.polys.forEach((poly) => {
      poly.forEach((ring) => {
        d += 'M' + ring.map((p) => `${tx(p[0])} ${ty(p[1])}`).join('L') + 'Z';
      });
      const outer = poly[0];
      if (!best || outer.length > best.n) {
        const cx = outer.reduce((s, p) => s + p[0], 0) / outer.length;
        const cy = outer.reduce((s, p) => s + p[1], 0) / outer.length;
        best = { n: outer.length, x: tx(cx), y: ty(cy) };
      }
    });
    return { name: f.name, area: f.area, d, cx: best && best.x, cy: best && best.y };
  });
  return { shapes, H };
}

const GeoMap = ({ tiles, metric = 'stage', highlight = [], onSelect }) => {
  const [geo, setGeo] = useState(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    loadGeo()
      .then((g) => alive && setGeo(g))
      .catch(() => alive && setFailed(true));
    return () => { alive = false; };
  }, []);

  const built = useMemo(() => (geo ? buildShapes(geo) : null), [geo]);

  const byState = useMemo(() => {
    const m = {};
    (tiles || []).forEach((t) => { m[t.state] = t; });
    return m;
  }, [tiles]);

  // If the GeoJSON can't be loaded, fall back to the tile grid.
  if (failed) return <TileMap tiles={tiles} metric={metric} highlight={highlight} onSelect={onSelect} />;
  if (!tiles || tiles.length === 0) return null;
  if (!built) return <div className="geomap-loading">Loading map…</div>;

  const colorOf = (t) => (!t ? CATEGORY_COLORS.no_data
    : metric === 'rainfall' ? rainfallColor(t.rainfall) : CATEGORY_COLORS[t.category]);
  const labelOf = (t) => (metric === 'rainfall'
    ? `${formatNumber(t.rainfall, 0)} mm`
    : `${formatNumber(t.stage, 1)}% - ${CATEGORY_LABELS[t.category]}`);

  const render = (s) => {
    const names = NAME_MAP[s.name] || [s.name];
    const stateName = names.find((n) => byState[n]);
    const t = stateName ? byState[stateName] : null;
    const isHi = names.some((n) => highlight.includes(n));
    const fill = colorOf(t);
    const title = t ? `${stateName}: ${labelOf(t)}` : `${s.name}: no data`;
    const click = () => stateName && onSelect && onSelect(stateName);
    const props = {
      role: 'button', tabIndex: stateName ? 0 : -1, 'aria-label': title,
      onClick: click,
      onKeyDown: (e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); click(); } },
    };
    return (
      <g key={s.name} className={`geo-state ${isHi ? 'geo-highlight' : ''}`} {...props}>
        <title>{title}</title>
        <path d={s.d} fill={fill} />
        {s.area < SMALL_AREA_KM2 && s.cx && (
          <circle cx={s.cx} cy={s.cy} r={5} fill={fill} className="geo-dot" />
        )}
      </g>
    );
  };

  return (
    <div className="tilemap-wrap geomap-wrap">
      <svg viewBox={`0 0 ${W} ${built.H}`} className="geomap" role="group" aria-label="Map of India">
        {built.shapes.map(render)}
      </svg>
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

export default GeoMap;