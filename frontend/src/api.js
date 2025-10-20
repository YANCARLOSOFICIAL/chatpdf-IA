import { API_BASE_URL } from './config'

// Simple token storage helpers
export function setToken(token) {
  if (token) localStorage.setItem('chatpdf_token', token)
  else localStorage.removeItem('chatpdf_token')
}

export function getToken() {
  return localStorage.getItem('chatpdf_token')
}

export function logout() {
  setToken(null)
}

// Login helper (expects backend /auth/login that returns { access_token } or { token })
export async function login(username, password) {
  const form = new FormData()
  form.append('username', username)
  form.append('password', password)
  const res = await fetch(`${API_BASE_URL}/auth/login`, { method: 'POST', body: form })
  if (!res.ok) {
    const txt = await res.text().catch(() => '')
    throw new Error(txt || `Login failed (status ${res.status})`)
  }
  const data = await res.json()
  const token = data.access_token || data.token || data.accessToken || data.jwt
  if (!token) throw new Error('No token returned from auth')
  setToken(token)
  return token
}

export async function register(username, password) {
  const form = new FormData()
  form.append('username', username)
  form.append('password', password)
  const res = await fetch(`${API_BASE_URL}/auth/register`, { method: 'POST', body: form })
  if (!res.ok) {
    const txt = await res.text().catch(() => '')
    throw new Error(txt || `Register failed (status ${res.status})`)
  }
  const data = await res.json()
  const token = data.token || data.access_token || data.jwt
  if (!token) throw new Error('No token returned from register')
  setToken(token)
  return { token, user: data.user }
}

export async function getMe() {
  const res = await fetch(`${API_BASE_URL}/auth/me`)
  if (!res.ok) return null
  try {
    const j = await res.json()
    return j
  } catch (e) {
    return null
  }
}

// Patch global fetch to automatically add Authorization header and prefix API base URL
const _origFetch = window.fetch.bind(window)
window.fetch = async function(input, init = {}) {
  try {
    let url = input
    // If input is a Request object
    if (input && input.url) url = input.url

    // Prefix relative paths with API_BASE_URL
    if (typeof url === 'string' && url.startsWith('/')) {
      url = API_BASE_URL + url
    } else if (typeof url === 'string' && !/^https?:\/\//i.test(url) && !url.startsWith(API_BASE_URL)) {
      // also handle paths like 'pdfs/..'
      url = API_BASE_URL + (url.startsWith('/') ? '' : '/') + url
    }

    // Ensure headers exist
    init = init || {}
    init.headers = init.headers || {}

    // If headers is a Headers instance, convert to plain object
    if (init.headers instanceof Headers) {
      const h = {}
      init.headers.forEach((v, k) => h[k] = v)
      init.headers = h
    }

    // Add Authorization if token present
    const token = getToken()
    if (token) {
      init.headers = { ...(init.headers || {}), Authorization: `Bearer ${token}` }
    }

    // Call original fetch
    return _origFetch(url, init)
  } catch (e) {
    return Promise.reject(e)
  }
}

export default {
  setToken,
  getToken,
  login,
  logout,
  register,
  getMe
}
