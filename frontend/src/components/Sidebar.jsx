import React, { useState } from 'react';
import { FaChevronDown, FaChevronUp, FaGlobe } from 'react-icons/fa';
import { LANGUAGES } from '../utils';

const QUICK = [
  'India overview',
  'Top 5 states by groundwater extraction',
  'Lowest rainfall states',
  'How many districts are over-exploited in India?',
];

const Sidebar = ({ states, language, setLanguage, onQuery, health, open, onClose }) => {
  const [showStates, setShowStates] = useState(false);
  const ai = health ? (health.gemini_configured ? 'Gemini AI on' : 'Offline rules mode') : 'Connecting…';

  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="sidebar-header">
        <h2>💧 INGRES</h2>
        <button type="button" className="sidebar-close" onClick={onClose} aria-label="Close menu">✕</button>
      </div>

      <div className="sidebar-section">
        <h3><FaGlobe /> Language</h3>
        <select className="language-select" value={language} onChange={(e) => setLanguage(e.target.value)}>
          {LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>{l.name}</option>
          ))}
        </select>
      </div>

      <div className="sidebar-section">
        <h3>⚡ Quick questions</h3>
        {QUICK.map((q) => (
          <button key={q} type="button" className="state-item" onClick={() => { onQuery(q); onClose(); }}>{q}</button>
        ))}
      </div>

      <div className="sidebar-section">
        <button type="button" className="section-header" onClick={() => setShowStates(!showStates)}>
          <h3>📍 States ({states.length})</h3>
          {showStates ? <FaChevronUp /> : <FaChevronDown />}
        </button>
        {showStates && (
          <div className="states-list">
            {states.map((state) => (
              <button key={state} type="button" className="state-item"
                      onClick={() => { onQuery(`Tell me about ${state}`); onClose(); }}>
                {state}
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        <p>{ai}</p>
        <p className="version">Data: CGWB 2024-25 · v4.0</p>
      </div>
    </aside>
  );
};

export default Sidebar;
