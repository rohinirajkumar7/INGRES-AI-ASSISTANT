import React, { useEffect, useRef, useState } from 'react';
import { FaMicrophone, FaPaperPlane } from 'react-icons/fa';
import { speechLang } from '../utils';

const SpeechRecognition = typeof window !== 'undefined'
  ? window.SpeechRecognition || window.webkitSpeechRecognition
  : undefined;

const InputBar = ({ onSend, language, disabled }) => {
  const [input, setInput] = useState('');
  const [listening, setListening] = useState(false);
  const recognitionRef = useRef(null);

  useEffect(() => () => {
    if (recognitionRef.current) recognitionRef.current.abort();
  }, []);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (input.trim() && !disabled) {
      onSend(input.trim());
      setInput('');
    }
  };

  const toggleListening = () => {
    if (!SpeechRecognition) return;
    if (listening && recognitionRef.current) {
      recognitionRef.current.stop();
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.lang = speechLang(language);
    recognition.interimResults = false;
    recognition.onresult = (event) => setInput(event.results[0][0].transcript);
    recognition.onend = () => setListening(false);
    recognition.onerror = () => setListening(false);
    recognitionRef.current = recognition;
    setListening(true);
    recognition.start();
  };

  return (
    <form className="input-bar" onSubmit={handleSubmit}>
      {SpeechRecognition && (
        <button type="button" className={`mic-button ${listening ? 'listening' : ''}`}
                onClick={toggleListening} aria-label="Speak your question">
          <FaMicrophone />
        </button>
      )}
      <input
        type="text"
        value={input}
        maxLength={500}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask about rainfall, recharge, extraction…"
        className="message-input"
        aria-label="Your question"
      />
      <button type="submit" className="send-button" disabled={!input.trim() || disabled} aria-label="Send">
        <FaPaperPlane />
      </button>
    </form>
  );
};

export default InputBar;
