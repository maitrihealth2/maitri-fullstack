import axios from 'axios'

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? 'https://maitri-fullstack-1.onrender.com').replace(/\/$/, '')

const api = axios.create({ baseURL: API_URL, timeout: 0, withCredentials: true })

let isRefreshing = false;
let failedQueue: any[] = [];

const processQueue = (error: any, token: string | null = null) => {
  failedQueue.forEach(prom => {
    if (error) {
      prom.reject(error);
    } else {
      prom.resolve(token);
    }
  });
  
  failedQueue = [];
}

api.interceptors.request.use((config) => {
  if (typeof window !== 'undefined') {
    const token = localStorage.getItem('mb_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (typeof window !== 'undefined' && !originalRequest.url?.includes('/api/auth/')) {
        if (isRefreshing) {
          return new Promise(function(resolve, reject) {
            failedQueue.push({ resolve, reject })
          }).then(token => {
            originalRequest.headers.Authorization = `Bearer ${token}`;
            return api(originalRequest);
          }).catch(err => {
            return Promise.reject(err);
          });
        }
        
        originalRequest._retry = true;
        isRefreshing = true;
        
        try {
          const { data } = await axios.post(`${API_URL}/api/auth/refresh`, {}, { withCredentials: true });
          
          const new_token = data.access_token;
          localStorage.setItem('mb_token', new_token);
          if (data.username) localStorage.setItem('mb_username', data.username);
          
          api.defaults.headers.common['Authorization'] = `Bearer ${new_token}`;
          originalRequest.headers.Authorization = `Bearer ${new_token}`;
          
          processQueue(null, new_token);
          return api(originalRequest);
        } catch (err) {
          processQueue(err, null);
          localStorage.removeItem('mb_token')
          localStorage.removeItem('mb_username')
          localStorage.removeItem('mb_language')
          document.cookie = 'mb_token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT'
          window.location.href = '/login'
          return Promise.reject(err);
        } finally {
          isRefreshing = false;
        }
      }
    }
    return Promise.reject(error)
  }
)

export default api

export async function register(username: string, email: string, password: string, language = 'en-IN') {
  const res = await api.post('/api/auth/register', { username, email, password, preferred_language: language })
  return res.data
}

export async function login(email: string, password: string) {
  const res = await api.post('/api/auth/login', { email, password })
  return res.data
}

export async function googleLogin(idToken: string) {
  const res = await api.post('/api/auth/google', { idToken })
  return res.data
}

export async function getMe() {
  const res = await api.get('/api/auth/me')
  return res.data
}

export async function getOnboardingStatus() {
  const res = await api.get('/api/user/onboarding/status')
  return res.data
}

export async function submitOnboarding(data: any) {
  const res = await api.post('/api/user/onboarding', data)
  return res.data
}

export async function startSession() {
  const res = await api.post('/api/consultation/start')
  return res.data
}

export async function sendMessage(session_id: string, message: string, language = 'en-IN') {
  const res = await api.post('/api/consultation/message', { session_id, message, language })
  return res.data
}

export async function getHistory() {
  const res = await api.get('/api/consultation/history')
  return res.data
}

export async function getTranscript(sessionId: string) {
  const res = await api.get(`/api/consultation/${sessionId}`)
  return res.data
}

export async function sendVoiceMessage(sessionId: string, formData: FormData) {
  const MAX_RETRIES = 3
  const RETRY_DELAY_MS = 2000

  for (let attempt = 1; attempt <= MAX_RETRIES; attempt++) {
    try {
      const token = typeof window !== 'undefined' ? localStorage.getItem('mb_token') : null
      const headers: Record<string, string> = {}
      if (token) headers['Authorization'] = `Bearer ${token}`

      const res = await fetch(`${API_URL}/api/voice/conversation`, {
        method: 'POST',
        headers,
        body: formData,
      })

      if (!res.ok) {
        const errText = await res.text()
        throw new Error(`Fetch failed with status ${res.status}: ${errText}`)
      }

      return await res.json()
    } catch (err: any) {
      // Only retry on pure network errors (server sleeping / unreachable).
      // HTTP errors (4xx/5xx) are real errors — don't retry those.
      const isNetworkError = err.message === 'Failed to fetch'
      if (isNetworkError && attempt < MAX_RETRIES) {
        console.warn(`[Voice] Network error on attempt ${attempt}/${MAX_RETRIES}, retrying in ${RETRY_DELAY_MS}ms...`)
        await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS))
        continue
      }
      console.error('FETCH ERROR DETAILED:', err.message)
      throw err
    }
  }
}

export async function getDashboardStats() {
  const res = await api.get('/api/consultation/dashboard_stats/overview')
  return res.data
}

export async function submitFeedback(content: string) {
  const res = await api.post('/api/feedback/submit', { content })
  return res.data
}
