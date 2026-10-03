import axios from 'axios';

// Same-origin '/api' works on Vercel and with the dev proxy (package.json "proxy").
// Override with REACT_APP_API_URL if the backend is hosted elsewhere.
export const API_URL = process.env.REACT_APP_API_URL || '/api';

export const api = axios.create({ baseURL: API_URL, timeout: 30000 });
