'use client'

import { useState } from 'react'
import { authApi } from '@/lib/api/auth'
import { Eye, EyeOff, CheckCircle2, XCircle } from 'lucide-react'

type PageState = 'form' | 'updating' | 'success'

function getStrength(pw: string): { score: number; label: string; color: string } {
  let score = 0
  if (pw.length >= 8) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  const map = [
    { label: 'Too weak', color: '#ef4444' },
    { label: 'Weak',     color: '#f97316' },
    { label: 'Fair',     color: '#eab308' },
    { label: 'Strong',   color: '#22c55e' },
    { label: 'Strong',   color: '#22c55e' },
  ]
  return { score, ...map[score] }
}

function PasswordInput({
  label, value, onChange, error, borderColor,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  error?: string
  borderColor?: string
}) {
  const [show, setShow] = useState(false)
  return (
    <div>
      <label style={{ fontSize: '14px', fontWeight: '500', color: '#374151', display: 'block', marginBottom: '8px' }}>
        {label}
      </label>
      <div style={{
        display: 'flex', alignItems: 'center',
        backgroundColor: '#f3f4f6',
        border: `1.5px solid ${borderColor ?? '#e5e7eb'}`,
        borderRadius: '10px', padding: '11px 14px', gap: '8px',
      }}>
        <input
          type={show ? 'text' : 'password'}
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            flex: 1, border: 'none', outline: 'none',
            backgroundColor: 'transparent', fontSize: '14px', color: '#111827',
          }}
        />
        <button
          type="button"
          onClick={() => setShow(s => !s)}
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', display: 'flex', padding: 0 }}
        >
          {show ? <Eye size={18} /> : <EyeOff size={18} />}
        </button>
      </div>
      {error && <p style={{ fontSize: '12px', color: '#ef4444', margin: '6px 0 0' }}>{error}</p>}
    </div>
  )
}

export default function SecurityPage() {
  const [current, setCurrent] = useState('')
  const [newPw, setNewPw] = useState('')
  const [confirm, setConfirm] = useState('')
  const [pageState, setPageState] = useState<PageState>('form')
  const [currentError, setCurrentError] = useState('')
  const [confirmError, setConfirmError] = useState('')

  const strength = getStrength(newPw)
  const showStrength = newPw.length > 0

  const checks = [
    { label: 'At least 1 uppercase', pass: /[A-Z]/.test(newPw) },
    { label: 'At least 1 number',    pass: /[0-9]/.test(newPw) },
    { label: 'At least 8 characters', pass: newPw.length >= 8 },
  ]

  const handleSubmit = async () => {
    setCurrentError('')
    setConfirmError('')

    if (!current || !newPw || !confirm) return

    if (newPw !== confirm) {
      setConfirmError('Passwords do not match')
      return
    }

    setPageState('updating')
    try {
      await authApi.changePassword({ current_password: current, new_password: newPw })
      setPageState('success')
    } catch (err: any) {
      setPageState('form')
      const detail = err?.response?.data?.detail ?? ''
      if (typeof detail === 'string' && detail.toLowerCase().includes('current')) {
        setCurrentError('Current password is incorrect')
      } else {
        setCurrentError('Current password is incorrect')
      }
    }
  }

  /* ── Success state ── */
  if (pageState === 'success') {
    return (
      <div style={{
        backgroundColor: 'white', border: '1px solid #e5e7eb',
        borderRadius: '16px', padding: '80px 40px',
        display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '12px',
      }}>
        <div style={{
          width: '56px', height: '56px', borderRadius: '50%',
          backgroundColor: '#dcfce7',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <CheckCircle2 size={28} color="#16a34a" />
        </div>
        <p style={{ fontSize: '18px', fontWeight: '700', color: '#111827', margin: 0 }}>
          Password updated successfully!
        </p>
        <p style={{ fontSize: '14px', color: '#6b7280', margin: 0, textAlign: 'center' }}>
          Your password has been changed successfully
        </p>
      </div>
    )
  }

  const isUpdating = pageState === 'updating'

  return (
    <div style={{
      backgroundColor: 'white', border: '1px solid #e5e7eb',
      borderRadius: '16px', padding: '48px 40px', maxWidth: '520px', margin: '0 auto',
    }}>
      {/* Heading */}
      <div style={{ textAlign: 'center', marginBottom: '32px' }}>
        <h2 style={{ fontSize: '20px', fontWeight: '700', color: '#111827', margin: '0 0 6px' }}>
          Change password
        </h2>
        <p style={{ fontSize: '13px', color: '#9ca3af', margin: 0 }}>
          Update your password to keep your account secure
        </p>
      </div>

      {/* Fields */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        <PasswordInput
          label="Current Password"
          value={current}
          onChange={v => { setCurrent(v); setCurrentError('') }}
          error={currentError}
          borderColor={currentError ? '#ef4444' : undefined}
        />

        <PasswordInput
          label="New Password"
          value={newPw}
          onChange={setNewPw}
        />

        {/* Confirm + strength */}
        <div>
          <PasswordInput
            label="New Password"
            value={confirm}
            onChange={v => { setConfirm(v); setConfirmError('') }}
            error={confirmError}
            borderColor={confirmError ? '#ef4444' : undefined}
          />

          {/* Password strength (shown when newPw has content) */}
          {showStrength && !confirmError && (
            <div style={{ marginTop: '10px' }}>
              {/* Strength bar */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginBottom: '8px' }}>
                <div style={{ display: 'flex', gap: '4px', flex: 1 }}>
                  {[0, 1, 2, 3].map(i => (
                    <div key={i} style={{
                      height: '4px', flex: 1, borderRadius: '2px',
                      backgroundColor: i < strength.score ? strength.color : '#e5e7eb',
                      transition: 'background-color 0.2s',
                    }} />
                  ))}
                </div>
                <span style={{ fontSize: '12px', color: strength.color, fontWeight: '500', whiteSpace: 'nowrap' }}>
                  {strength.label}
                </span>
              </div>
              {/* Checklist */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                {checks.map(c => (
                  <div key={c.label} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    {c.pass
                      ? <CheckCircle2 size={14} color="#16a34a" />
                      : <XCircle size={14} color="#9ca3af" />
                    }
                    <span style={{ fontSize: '12px', color: c.pass ? '#16a34a' : '#9ca3af' }}>{c.label}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Submit */}
      <button
        onClick={handleSubmit}
        disabled={isUpdating}
        style={{
          width: '100%', marginTop: '28px',
          backgroundColor: isUpdating ? '#bfdbfe' : '#2563eb',
          color: isUpdating ? '#2563eb' : 'white',
          border: 'none', borderRadius: '10px',
          padding: '13px', fontSize: '15px', fontWeight: '600',
          cursor: isUpdating ? 'not-allowed' : 'pointer',
          transition: 'background-color 0.2s',
        }}
      >
        {isUpdating ? 'Updating...' : 'Update password'}
      </button>
    </div>
  )
}
