import { api } from './client'

export const walletApi = {
  balance: () =>
    api.get('/api/v1/wallet/balance'),

  transactions: () =>
    api.get('/api/v1/wallet/transactions'),

  summary: () =>
    api.get('/api/v1/wallet/summary'),
}