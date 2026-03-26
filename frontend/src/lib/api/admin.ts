import { api } from './client'

export const adminApi = {
  dashboard: () =>
    api.get('/api/v1/admin/dashboard'),

  register: (data: object) =>
    api.post('/api/v1/admin/register', data),

  orgs: () =>
    api.get('/api/v1/admin/organizations'),

  org: (id: string) =>
    api.get(`/api/v1/admin/organizations/${id}`),

  updateOrg: (id: string, data: { name?: string; is_active?: boolean }) =>
    api.patch(`/api/v1/admin/organizations/${id}`, data),

  deleteOrg: (id: string) =>
    api.delete(`/api/v1/admin/organizations/${id}`),

  orgUsers: (id: string) =>
    api.get(`/api/v1/admin/organizations/${id}/users`),

  orgCampaigns: (id: string) =>
    api.get(`/api/v1/admin/organizations/${id}/campaigns`),

  orgMinutes: (id: string) =>
    api.get(`/api/v1/admin/organizations/${id}/minutes`),

  orgWallet: (id: string) =>
    api.get(`/api/v1/admin/organizations/${id}/wallet`),

  creditWallet: (id: string, data: { minutes: number; rate_per_minute: number; description?: string }) =>
    api.post(`/api/v1/admin/organizations/${id}/wallet/credit`, data),

  campaigns: () =>
    api.get('/api/v1/admin/campaigns'),

  users: () =>
    api.get('/api/v1/admin/users'),

  toggleUser: (userId: string) =>
    api.patch(`/api/v1/admin/users/${userId}/toggle-status`),
}