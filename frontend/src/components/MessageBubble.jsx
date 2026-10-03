import React from 'react';
import { FaVolumeUp } from 'react-icons/fa';
import ChartDisplay from './ChartDisplay';
import DataCard from './DataCard';
import { speechLang } from '../utils';

const canSpeak = typeof window !== 'undefined' && 'speechSynthesis' in window;

function speak(text, language) {
  if (!canSpeak) return;
  window.speechSynthesis.cancel();
  const utterance = new window.SpeechSynthesisUtterance(text);
  utterance.lang = speechLang(language);
  window.speechSynthesis.speak(utterance);
}

const MessageBubble = ({ message, onSuggestionClick, onStateSelect }) => (
  <div className={`message-bubble ${message.type}`}>
    <div className="message-content">
      <p className="message-text">{message.text}</p>

      {message.notice && <p className="message-notice">ℹ️ {message.notice}</p>}

      {message.charts && message.charts.map((chart, idx) => (
        <ChartDisplay key={idx} chart={chart} onStateSelect={onStateSelect} />
      ))}

      {message.data && message.data.length > 0 && (
        <div className="data-cards">
          {message.data.map((item) => (
            <DataCard key={`${item.subtitle}-${item.name}`} data={item} />
          ))}
        </div>
      )}

      {message.suggestions && message.suggestions.length > 0 && (
        <div className="suggestions">
          <span className="suggestions-label">Try:</span>
          {message.suggestions.map((s) => (
            <button key={s} type="button" className="suggestion-chip" onClick={() => onSuggestionClick(s)}>
              {s}
            </button>
          ))}
        </div>
      )}
    </div>
    <div className="message-meta">
      <span className="message-time">{message.timestamp}</span>
      {message.type === 'bot' && message.source && (
        <span className="source-badge">{message.source === 'gemini' ? '✨ Gemini' : '🧩 Offline rules'}</span>
      )}
      {message.type === 'bot' && canSpeak && (
        <button type="button" className="speak-button" aria-label="Read aloud"
                onClick={() => speak(message.text, message.language || 'en')}>
          <FaVolumeUp />
        </button>
      )}
    </div>
  </div>
);

export default MessageBubble;
