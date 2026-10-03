import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from './api';
import ChatWindow from './components/ChatWindow';
import Sidebar from './components/Sidebar';
import './App.css';

function App() {
  const [language, setLanguage] = useState('en');
  const [states, setStates] = useState([]);
  const [health, setHealth] = useState(null);
  const [pendingQuery, setPendingQuery] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const queryId = useRef(1);

  useEffect(() => {
    api.get('/states').then((res) => setStates(res.data)).catch(() => {});
    api.get('/health').then((res) => setHealth(res.data)).catch(() => {});
  }, []);

  const runQuery = useCallback((text) => {
    setPendingQuery({ id: queryId.current++, text });
  }, []);

  return (
    <div className="app-container">
      <Sidebar
        states={states}
        language={language}
        setLanguage={setLanguage}
        onQuery={runQuery}
        health={health}
        open={menuOpen}
        onClose={() => setMenuOpen(false)}
      />
      <div className="main-content">
        <header className="app-header">
          <button type="button" className="menu-button" onClick={() => setMenuOpen(true)} aria-label="Open menu">☰</button>
          <div>
            <h1>INGRES AI Assistant</h1>
            <p>India's groundwater data, in plain language · CGWB 2024-25 assessment</p>
          </div>
        </header>
        <ChatWindow language={language} pendingQuery={pendingQuery} />
      </div>
    </div>
  );
}

export default App;
