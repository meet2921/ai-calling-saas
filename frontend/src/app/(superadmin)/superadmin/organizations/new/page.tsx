'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { adminApi } from '@/lib/api/admin'
import { Eye, EyeOff, Copy, Check } from 'lucide-react'
import { toast } from 'sonner'

interface FormData {
  org_name: string
  org_slug: string
  first_name: string
  last_name: string
  email: string
  password: string
  initial_minutes: string
  rate_per_minute: string
}

interface CreatedOrg {
  name: string
  slug: string
  email: string
  password: string
}

function getPasswordStrength(pw: string): { score: number; label: string; color: string } {
  if (!pw) return { score: 0, label: '', color: '#e5e7eb' }
  let score = 0
  if (pw.length >= 8) score++
  if (/[A-Z]/.test(pw)) score++
  if (/[0-9]/.test(pw)) score++
  if (/[^A-Za-z0-9]/.test(pw)) score++
  const map = [
    { label: 'Too weak', color: '#ef4444' },
    { label: 'Weak', color: '#f97316' },
    { label: 'Fair', color: '#eab308' },
    { label: 'Strong', color: '#22c55e' },
    { label: 'Very strong', color: '#16a34a' },
  ]
  return { score, ...map[score] }
}

function SectionCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div style={{
      backgroundColor: 'white', border: '1px solid #e5e7eb',
      borderRadius: '16px', padding: '24px',
    }}>
      <h2 style={{ fontSize: '15px', fontWeight: '700', color: '#2563eb', marginBottom: '20px' }}>{title}</h2>
      {children}
    </div>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label style={{ fontSize: '13px', fontWeight: '500', color: '#374151', display: 'block', marginBottom: '8px' }}>
        {label}
      </label>
      {children}
    </div>
  )
}

function InputStyle({ hint, ...props }: React.InputHTMLAttributes<HTMLInputElement> & { hint?: string }) {
  return (
    <div>
      <input
        {...props}
        style={{
          width: '100%', border: '1px solid #e5e7eb', borderRadius: '10px',
          padding: '11px 14px', fontSize: '14px', color: '#111827',
          backgroundColor: '#f9fafb', outline: 'none', boxSizing: 'border-box',
          ...props.style,
        }}
        onFocus={e => (e.currentTarget.style.borderColor = '#93c5fd')}
        onBlur={e => (e.currentTarget.style.borderColor = '#e5e7eb')}
      />
      {hint && <p style={{ fontSize: '11px', color: '#9ca3af', marginTop: '4px' }}>{hint}</p>}
    </div>
  )
}

export default function RegisterOrgPage() {
  const router = useRouter()
  const [form, setForm] = useState<FormData>({
    org_name: '',
    org_slug: '',
    first_name: '',
    last_name: '',
    email: '',
    password: '',
    initial_minutes: '100',
    rate_per_minute: '10.00',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [created, setCreated] = useState<CreatedOrg | null>(null)
  const [copied, setCopied] = useState<'email' | 'password' | null>(null)
  const [showCreatedPw, setShowCreatedPw] = useState(false)

  const set = (key: keyof FormData) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value
    setForm(prev => {
      const next = { ...prev, [key]: val }
      // Auto-generate slug from org name
      if (key === 'org_name') {
        next.org_slug = val.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '')
      }
      return next
    })
  }

  const strength = getPasswordStrength(form.password)

  const copyToClipboard = async (text: string, field: 'email' | 'password') => {
    await navigator.clipboard.writeText(text)
    setCopied(field)
    setTimeout(() => setCopied(null), 2000)
  }

  const handleSubmit = async () => {
    if (!form.org_name || !form.org_slug || !form.first_name || !form.email || !form.password) {
      toast.error('Please fill in all required fields')
      return
    }
    setSubmitting(true)
    try {
      const res = await adminApi.register({
        org_name: form.org_name,
        org_slug: form.org_slug,
        first_name: form.first_name,
        last_name: form.last_name,
        email: form.email,
        password: form.password,
        initial_minutes: Number(form.initial_minutes) || 0,
        rate_per_minute: Number(form.rate_per_minute) || 0,
      })
      setCreated({
        name: res.data?.org_name ?? form.org_name,
        slug: res.data?.org_slug ?? form.org_slug,
        email: form.email,
        password: form.password,
      })
    } catch (err: any) {
      toast.error(err?.response?.data?.detail ?? 'Failed to create organization')
    } finally {
      setSubmitting(false)
    }
  }

  const resetForm = () => {
    setForm({ org_name: '', org_slug: '', first_name: '', last_name: '', email: '', password: '', initial_minutes: '100', rate_per_minute: '10.00' })
    setCreated(null)
    setShowCreatedPw(false)
  }

  return (
    <>
      <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', maxWidth: '900px' }}>

        {/* Organizations section */}
        <SectionCard title="Organizations">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <Field label="Organization name">
              <InputStyle placeholder="Acme corporation" value={form.org_name} onChange={set('org_name')} />
            </Field>
            <Field label="Organization slug">
              <InputStyle
                placeholder="acme-corporation"
                value={form.org_slug}
                onChange={set('org_slug')}
                hint="Lowercase letters, numbers and hyphens only."
              />
            </Field>
          </div>
        </SectionCard>

        {/* Admin user section */}
        <SectionCard title="Admin user">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <Field label="First name">
              <InputStyle placeholder="Rajiv" value={form.first_name} onChange={set('first_name')} />
            </Field>
            <Field label="Last name">
              <InputStyle placeholder="Kulkarni" value={form.last_name} onChange={set('last_name')} />
            </Field>
            <Field label="Email address">
              <InputStyle type="email" placeholder="Rajiv@gmail.com" value={form.email} onChange={set('email')} />
            </Field>
            <Field label="Password">
              <div style={{ position: 'relative' }}>
                <input
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••"
                  value={form.password}
                  onChange={set('password')}
                  style={{
                    width: '100%', border: '1px solid #e5e7eb', borderRadius: '10px',
                    padding: '11px 42px 11px 14px', fontSize: '14px', color: '#111827',
                    backgroundColor: '#f9fafb', outline: 'none', boxSizing: 'border-box',
                  }}
                  onFocus={e => (e.currentTarget.style.borderColor = '#93c5fd')}
                  onBlur={e => (e.currentTarget.style.borderColor = '#e5e7eb')}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(v => !v)}
                  style={{
                    position: 'absolute', right: '12px', top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: 0, display: 'flex',
                  }}
                >
                  {showPassword ? <Eye size={16} /> : <EyeOff size={16} />}
                </button>
              </div>
              {/* Strength bar */}
              {form.password && (
                <div style={{ marginTop: '6px' }}>
                  <div style={{ display: 'flex', gap: '4px', marginBottom: '4px' }}>
                    {[0, 1, 2, 3].map(i => (
                      <div
                        key={i}
                        style={{
                          flex: 1, height: '3px', borderRadius: '2px',
                          backgroundColor: i < strength.score ? strength.color : '#e5e7eb',
                          transition: 'background-color 0.2s',
                        }}
                      />
                    ))}
                  </div>
                  <p style={{ fontSize: '11px', color: strength.color, fontWeight: '500' }}>{strength.label}</p>
                </div>
              )}
            </Field>
          </div>
        </SectionCard>

        {/* Wallet section */}
        <SectionCard title="Wallet">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
            <Field label="Initial minutes to load">
              <InputStyle type="number" placeholder="100" value={form.initial_minutes} onChange={set('initial_minutes')} />
            </Field>
            <Field label="Rate per minute (INR)">
              <InputStyle type="number" placeholder="10.00" value={form.rate_per_minute} onChange={set('rate_per_minute')} />
            </Field>
          </div>
        </SectionCard>

        {/* Submit */}
        <div style={{ display: 'flex', justifyContent: 'center', paddingBottom: '16px' }}>
          <button
            onClick={handleSubmit}
            disabled={submitting}
            style={{
              backgroundColor: submitting ? '#93c5fd' : '#2563eb', color: 'white',
              border: 'none', borderRadius: '50px', padding: '13px 48px',
              fontSize: '14px', fontWeight: '600', cursor: submitting ? 'not-allowed' : 'pointer',
              transition: 'background-color 0.15s',
            }}
          >
            {submitting ? 'Creating…' : 'Create organization'}
          </button>
        </div>
      </div>

      {/* Success Modal */}
      {created && (
        <div style={{
          position: 'fixed', inset: 0, zIndex: 100,
          backgroundColor: 'rgba(0,0,0,0.45)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          padding: '16px',
        }}>
          <div style={{
            backgroundColor: 'white', borderRadius: '20px',
            padding: '32px', width: '100%', maxWidth: '460px',
            boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
          }}>
            {/* Icon */}
            <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '16px' }}>
              <div style={{
                width: '56px', height: '56px', borderRadius: '50%',
                backgroundColor: '#f0fdf4', border: '4px solid #bbf7d0',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Check size={24} style={{ color: '#16a34a' }} />
              </div>
            </div>

            <h2 style={{ fontSize: '18px', fontWeight: '700', color: '#111827', textAlign: 'center', marginBottom: '6px' }}>
              Organization created successfully
            </h2>
            <p style={{ fontSize: '13px', color: '#6b7280', textAlign: 'center', marginBottom: '20px' }}>
              Your organization has been registered and is ready to use
            </p>

            {/* Details */}
            <div style={{ border: '1px solid #e5e7eb', borderRadius: '12px', overflow: 'hidden', marginBottom: '16px' }}>
              {[
                { label: 'Organization Name', value: created.name },
                { label: 'Organization Slug', value: created.slug },
              ].map(({ label, value }, i) => (
                <div key={label} style={{
                  padding: '12px 16px',
                  borderBottom: i === 1 ? '1px solid #e5e7eb' : 'none',
                }}>
                  <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>{label}</p>
                  <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>{value}</p>
                </div>
              ))}

              {/* Email with copy */}
              <div style={{ padding: '12px 16px', borderBottom: '1px solid #e5e7eb', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>Admin Email</p>
                  <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>{created.email}</p>
                </div>
                <button
                  onClick={() => copyToClipboard(created.email, 'email')}
                  style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: '4px', display: 'flex' }}
                  title="Copy email"
                >
                  {copied === 'email' ? <Check size={16} style={{ color: '#16a34a' }} /> : <Copy size={16} />}
                </button>
              </div>

              {/* Password with show + copy */}
              <div style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div>
                  <p style={{ fontSize: '11px', color: '#9ca3af', marginBottom: '2px' }}>Admin Password</p>
                  <p style={{ fontSize: '14px', fontWeight: '600', color: '#111827', letterSpacing: showCreatedPw ? '0' : '3px' }}>
                    {showCreatedPw ? created.password : '•'.repeat(Math.min(created.password.length, 10))}
                  </p>
                </div>
                <div style={{ display: 'flex', gap: '6px' }}>
                  <button
                    onClick={() => setShowCreatedPw(v => !v)}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: '4px', display: 'flex' }}
                    title={showCreatedPw ? 'Hide' : 'Show'}
                  >
                    {showCreatedPw ? <Eye size={16} /> : <EyeOff size={16} />}
                  </button>
                  <button
                    onClick={() => copyToClipboard(created.password, 'password')}
                    style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#9ca3af', padding: '4px', display: 'flex' }}
                    title="Copy password"
                  >
                    {copied === 'password' ? <Check size={16} style={{ color: '#16a34a' }} /> : <Copy size={16} />}
                  </button>
                </div>
              </div>
            </div>

            {/* Warning */}
            <div style={{
              backgroundColor: '#fffbeb', border: '1px solid #fde68a',
              borderRadius: '8px', padding: '10px 14px', marginBottom: '20px',
            }}>
              <p style={{ fontSize: '12px', color: '#92400e' }}>
                <strong>Important:</strong> Please save these credentials securely. The password won&apos;t be shown again.
              </p>
            </div>

            {/* Actions */}
            <div style={{ display: 'flex', gap: '10px' }}>
              <button
                onClick={resetForm}
                style={{
                  flex: 1, padding: '11px', border: '1px solid #e5e7eb',
                  borderRadius: '50px', backgroundColor: 'white',
                  fontSize: '13px', fontWeight: '600', color: '#374151', cursor: 'pointer',
                }}
              >
                Register Another Organization
              </button>
              <button
                onClick={() => router.push('/superadmin/organizations')}
                style={{
                  flex: 1, padding: '11px', border: 'none',
                  borderRadius: '50px', backgroundColor: '#2563eb',
                  fontSize: '13px', fontWeight: '600', color: 'white', cursor: 'pointer',
                }}
              >
                Go to Organizations
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  )
}
