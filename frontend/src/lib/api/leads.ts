import { api } from './client'

export const leadsApi = {
  upload: (campaignId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/api/v1/campaigns/${campaignId}/leads/upload`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },

  list: (campaignId: string, page = 1, pageSize = 50) =>
    api.get(`/api/v1/campaigns/${campaignId}/leads`, {
      params: { page, page_size: pageSize },
    }),

  delete: (campaignId: string, leadId: string) =>
    api.delete(`/api/v1/campaigns/${campaignId}/leads/${leadId}`),

  getStatus: (campaignId: string, leadId: string) =>
    api.get(`/api/v1/campaigns/${campaignId}/leads/${leadId}/lead-status`),
}