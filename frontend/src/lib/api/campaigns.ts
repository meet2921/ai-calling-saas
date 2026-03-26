import { api } from './client'

export const campaignsApi = {
  list: () =>
    api.get('/api/v1/campaigns/'),

  create: (data: { name: string; description?: string; bolna_agent_id: string }) =>
    api.post('/api/v1/campaigns/', data),

  get: (id: string) =>
    api.get(`/api/v1/campaigns/${id}`),

  update: (id: string, data: { name: string; description?: string; bolna_agent_id: string }) =>
    api.put(`/api/v1/campaigns/${id}/update`, data),

  delete: (id: string) =>
    api.delete(`/api/v1/campaigns/${id}`),

  getAgent: (id: string) =>
    api.get(`/api/v1/campaigns/${id}/agent`),

  start: (id: string) =>
    api.post(`/api/v1/campaigns/${id}/start`),

  pause: (id: string) =>
    api.post(`/api/v1/campaigns/${id}/pause`),

  resume: (id: string) =>
    api.post(`/api/v1/campaigns/${id}/resume`),

  stop: (id: string) =>
    api.post(`/api/v1/campaigns/${id}/stop`),
}