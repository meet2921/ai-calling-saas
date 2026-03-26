'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { campaignsApi } from '@/lib/api/campaigns'
import { toast } from 'sonner'

export default function CreateCampaignPage() {
  const router = useRouter()
  const [form, setForm] = useState({ name: '', bolna_agent_id: '', description: '' })
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!form.name.trim() || !form.bolna_agent_id.trim()) {
      toast.error('Campaign name and Bolna Agent ID are required')
      return
    }
    setLoading(true)
    try {
      await campaignsApi.create({
        name: form.name,
        bolna_agent_id: form.bolna_agent_id,
        ...(form.description.trim() ? { description: form.description } : {}),
      })
      toast.success('Campaign created successfully')
      router.push('/campaigns')
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to create campaign')
    } finally {
      setLoading(false)
    }
  }

  const inputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px 14px',
    borderRadius: '10px',
    border: 'none',
    backgroundColor: '#eef2ff',
    fontSize: '14px',
    color: '#374151',
    outline: 'none',
    boxSizing: 'border-box',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

      {/* Form card */}
      <div style={{
        backgroundColor: 'white',
        border: '1px solid #e5e7eb',
        borderRadius: '14px',
        padding: '28px 32px',
      }}>
        <p style={{ fontSize: '16px', fontWeight: '700', color: '#2563eb', marginBottom: '24px' }}>
          Campaign info
        </p>

        {/* Row 1: name + agent id */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>
          <div>
            <label style={{ fontSize: '14px', fontWeight: '500', color: '#111827', display: 'block', marginBottom: '8px' }}>
              Campaign Name
            </label>
            <input
              type="text"
              placeholder="Customer feedback campaign"
              value={form.name}
              onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
              style={inputStyle}
            />
          </div>
          <div>
            <label style={{ fontSize: '14px', fontWeight: '500', color: '#111827', display: 'block', marginBottom: '8px' }}>
              Bolna Agent ID
            </label>
            <input
              type="text"
              placeholder="AGX-xxxx"
              value={form.bolna_agent_id}
              onChange={e => setForm(f => ({ ...f, bolna_agent_id: e.target.value }))}
              style={inputStyle}
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <label style={{ fontSize: '14px', fontWeight: '500', color: '#111827', display: 'block', marginBottom: '8px' }}>
            Description (Optional)
          </label>
          <textarea
            placeholder="Short description about what the campaign is for.."
            value={form.description}
            onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
            rows={5}
            style={{ ...inputStyle, resize: 'vertical', fontFamily: 'inherit', lineHeight: '1.5' }}
          />
        </div>
      </div>

      {/* Submit */}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <button
          onClick={handleSubmit}
          disabled={loading}
          style={{
            backgroundColor: '#2563eb',
            color: 'white',
            border: 'none',
            borderRadius: '10px',
            padding: '13px 52px',
            fontSize: '15px',
            fontWeight: '600',
            cursor: loading ? 'not-allowed' : 'pointer',
            opacity: loading ? 0.7 : 1,
          }}
        >
          {loading ? 'Creating...' : 'Create campaign'}
        </button>
      </div>
    </div>
  )
}
