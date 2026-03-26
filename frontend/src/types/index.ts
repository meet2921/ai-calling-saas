export type UserRole = 'super_admin' | 'admin'

export type CampaignStatus = 'draft' | 'running' | 'paused' | 'stopped' | 'completed'

export type LeadStatus = 'pending' | 'queued' | 'calling' | 'completed' | 'failed'

export type TransactionType = 'credit' | 'debit'

export interface User {
  id: string
  email: string
  first_name: string
  last_name: string
  role: UserRole
  organization_id: string
  org_name: string
  org_slug: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface Campaign {
  id: string
  name: string
  description: string | null
  bolna_agent_id: string | null
  status: CampaignStatus
  created_at: string
  updated_at: string | null
}

export interface Lead {
  id: string
  phone: string
  status: LeadStatus
  custom_fields: Record<string, string>
  created_at: string
}

export interface WalletBalance {
  minutes_balance: number
  rate_per_minute: number
}

export interface WalletSummary {
  minutes_balance: number
  rate_per_minute: number
  total_minutes_purchased: number
  total_minutes_used: number
  total_amount_paid: number
  estimated_cost_remaining: number
}

export interface WalletTransaction {
  id: string
  type: TransactionType
  minutes: number
  amount_inr: number
  rate_per_minute: number
  balance_after: number
  description: string
  call_log_id: string | null
  created_at: string
}

export interface CallLog {
  id: string
  campaign_id: string
  lead_id: string | null
  user_number: string | null
  duration: number
  cost: number
  status: string | null
  recording_url: string | null
  transcript: string | null
  executed_at: string
  interest_level: string | null
  appointment_booked: boolean
  customer_sentiment: string | null
  final_call_summary: string | null
}

export interface Organization {
  id: string
  name: string
  slug: string
  is_active: boolean
  created_at: string
}

export interface AdminDashboard {
  organizations: {
    total: number
    active: number
    suspended: number
  }
  users: {
    total_admins: number
  }
  calls: {
    total_calls: number
    total_minutes_used: number
  }
  revenue: {
    total_amount_paid_inr: number
  }
  alerts: {
    orgs_with_zero_balance: number
  }
  campaigns: {
    total: number
  }
}