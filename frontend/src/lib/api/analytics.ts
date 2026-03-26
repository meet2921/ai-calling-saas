import { api } from './client'

export const analyticsApi = {
  get: (campaignId: string) =>
    api.get(`/api/v1/campaigns/${campaignId}/analytics`),

  logs: (campaignId: string) =>
    api.get(`/api/v1/campaigns/${campaignId}/logs`),
}