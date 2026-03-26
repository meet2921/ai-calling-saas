import { api } from './client'

export const authApi = {
  login: (data: { org_slug: string; email: string; password: string }) =>
    api.post('/api/v1/auth/login', data),

  refresh: (refresh_token: string) =>
    api.post('/api/v1/auth/refresh', { refresh_token }),

  me: () => api.get('/api/v1/auth/me'),

  updateMe: (data: { first_name?: string; last_name?: string; email?: string }) =>
    api.put('/api/v1/auth/me', data),

  logout: (refresh_token: string) =>
    api.post('/api/v1/auth/logout', { refresh_token }),

  forgotPassword: (data: { org_slug: string; email: string }) =>
    api.post('/api/v1/auth/forgot-password', data),

  resetPassword: (data: { reset_token: string; new_password: string }) =>
    api.post('/api/v1/auth/reset-password', data),

  changePassword: (data: { current_password: string; new_password: string }) =>
    api.put('/api/v1/auth/me/password', data),
}