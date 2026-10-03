import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api';
import MessageBubble from './MessageBubble';
import InputBar from './InputBar';

const now = () => new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

const WELCOME = {
  id: 0,
  type: 'bot',
  text: "Hello! I'm the INGRES groundwater assistant. Tap a state on the map or ask me anything about rainfall, recharge, extraction and water availability.",
  timestamp: now(),
  suggestions: ['Rainfall in Bengaluru', 'Most over-exploited districts in Punjab', 'Compare Karnataka and Kerala', 'Top 5 states by groundwater extraction'],
};

const ChatWindow = ({ language, pendingQuery }) => {
  const [messages, setMessages] = useState([WELCOME]);
  const [isTyping, setIsTyping] = useState(false);
  const endRef = useRef(null);
  const nextId = useRef(1);
  const contextRef = useRef(null);
  const handledQuery = useRef(0);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  // Show the India map in the welcome message.
  useEffect(() => {
    let cancelled = false;
    api.get('/map')
      .then((res) => {
        if (cancelled) return;
        const chart = { type: 'map', title: 'Groundwater extraction category by state (tap a state)', metric: 'stage', data: res.data.tiles, highlight: [] };
        setMessages((prev) => prev.map((m) => (m.id === 0 ? { ...m, charts: [chart] } : m)));
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);

  const sendMessage = useCallback(async (text) => {
    const clean = text.trim();
    if (!clean) return;
    setMessages((prev) => [...prev, { id: nextId.current++, type: 'user', text: clean, timestamp: now() }]);
    setIsTyping(true);
    try {
      const res = await api.post('/chat', { message: clean, language, context: contextRef.current });
      const d = res.data;
      contextRef.current = d.context && Object.keys(d.context).length ? d.context : null;
      setMessages((prev) => [...prev, {
        id: nextId.current++, type: 'bot', text: d.response, data: d.data, charts: d.charts,
        suggestions: d.suggestions, notice: d.notice, source: d.source, language: d.language, timestamp: now(),
      }]);
    } catch (error) {
      const unreachable = !error.response;
      const text = unreachable
        ? 'I could not reach the server. Please check your connection and try again.'
        : 'Sorry, something went wrong while answering. Please try again.';
      setMessages((prev) => [...prev, { id: nextId.current++, type: 'bot', text, timestamp: now() }]);
    } finally {
      setIsTyping(false);
    }
  }, [language]);

  // Sidebar / map clicks. The ref guard stops a re-send when the language changes.
  useEffect(() => {
    if (pendingQuery && pendingQuery.id !== handledQuery.current) {
      handledQuery.current = pendingQuery.id;
      sendMessage(pendingQuery.text);
    }
  }, [pendingQuery, sendMessage]);

  return (
    <div className="chat-window">
      <div className="messages-container">
        {messages.map((msg) => (
          <MessageBubble
            key={msg.id}
            message={msg}
            onSuggestionClick={sendMessage}
            onStateSelect={(state) => sendMessage(`Tell me about ${state}`)}
          />
        ))}
        {isTyping && (
          <div className="typing-indicator">
            <div className="typing-dots"><span /><span /><span /></div>
            <span className="typing-text">INGRES is thinking…</span>
          </div>
        )}
        <div ref={endRef} />
      </div>
      <InputBar onSend={sendMessage} language={language} disabled={isTyping} />
    </div>
  );
};

export default ChatWindow;
