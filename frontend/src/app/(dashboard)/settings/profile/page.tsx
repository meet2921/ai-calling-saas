'use client'

import { useEffect, useState, useRef } from 'react'
import { authApi } from '@/lib/api/auth'
import { useAuthStore } from '@/store/auth.store'
import { Pencil } from 'lucide-react'
import { toast } from 'sonner'

interface UserData {
  first_name: string
  last_name: string
  email: string
  role: string
  org_name: string
}

const fieldBox: React.CSSProperties = {
  backgroundColor: '#f3f4f6',
  borderRadius: '10px',
  padding: '10px 14px',
}

const fieldLabel: React.CSSProperties = {
  fontSize: '11px',
  color: '#9ca3af',
  marginBottom: '4px',
  margin: '0 0 4px',
}

const fieldValue: React.CSSProperties = {
  fontSize: '14px',
  fontWeight: '500',
  color: '#111827',
  margin: 0,
}

export default function ProfilePage() {
  const { setUser } = useAuthStore()

  const [userData, setUserData] = useState<UserData>({
    first_name: '',
    last_name: '',
    email: '',
    role: '',
    org_name: '',
  })

  const [editPersonal, setEditPersonal] = useState(false)
  const [savingPersonal, setSavingPersonal] = useState(false)

  useEffect(() => {
    authApi.me().then(res => {
      const d = res.data
      setUserData({
        first_name: d.first_name ?? '',
        last_name: d.last_name ?? '',
        email: d.email ?? '',
        role: d.role ?? '',
        org_name: d.org_name ?? '',
      })
    }).catch(() => {})
  }, [])

  const savePersonal = async () => {
    setSavingPersonal(true)
    try {
      const res = await authApi.updateMe({
        first_name: userData.first_name,
        last_name: userData.last_name,
        email: userData.email,
      })
      setUser(res.data)
      toast.success('Profile updated')
      setEditPersonal(false)
    } catch {
      toast.error('Failed to update profile')
    } finally {
      setSavingPersonal(false)
    }
  }

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [avatarUrl, setAvatarUrl] = useState<string | null>(() => {
    if (typeof window !== 'undefined') return localStorage.getItem('profile_avatar')
    return null
  })

  const handleAvatarUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = () => {
      const url = reader.result as string
      setAvatarUrl(url)
      localStorage.setItem('profile_avatar', url)
      toast.success('Profile photo updated')
    }
    reader.readAsDataURL(file)
    e.target.value = ''
  }

  const handleDeleteAvatar = () => {
    setAvatarUrl(null)
    localStorage.removeItem('profile_avatar')
    toast.success('Profile photo removed')
  }

  const initials = ((userData.first_name?.[0] ?? '') + (userData.last_name?.[0] ?? '')).toUpperCase()

  const editBtn = (onClick: () => void) => (
    <button
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '6px',
        backgroundColor: 'white', color: '#2563eb',
        border: '1.5px solid #2563eb', borderRadius: '8px',
        padding: '7px 16px', fontSize: '13px', fontWeight: '600', cursor: 'pointer',
      }}
    >
      <Pencil size={13} /> Edit
    </button>
  )

  const saveCancel = (onSave: () => void, onCancel: () => void, saving?: boolean) => (
    <div style={{ display: 'flex', gap: '10px' }}>
      <button
        onClick={onCancel}
        style={{
          backgroundColor: 'white', color: '#6b7280', border: '1px solid #e5e7eb',
          borderRadius: '8px', padding: '7px 16px', fontSize: '13px', fontWeight: '600', cursor: 'pointer',
        }}
      >
        Cancel
      </button>
      <button
        onClick={onSave}
        disabled={saving}
        style={{
          backgroundColor: '#2563eb', color: 'white', border: 'none',
          borderRadius: '8px', padding: '7px 16px', fontSize: '13px',
          fontWeight: '600', cursor: 'pointer', opacity: saving ? 0.7 : 1,
        }}
      >
        {saving ? 'Saving...' : 'Save'}
      </button>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>

      {/* Avatar card */}
      <div style={{
        backgroundColor: 'white', border: '1px solid #e5e7eb',
        borderRadius: '16px', padding: '24px 28px',
        display: 'flex', alignItems: 'center', gap: '20px',
      }}>
        {/* Hidden file input */}
        <input
          ref={fileInputRef}
          type="file"
          accept="image/*"
          style={{ display: 'none' }}
          onChange={handleAvatarUpload}
        />

        {/* Avatar circle */}
        {avatarUrl ? (
          <img
            src={avatarUrl}
            alt="avatar"
            style={{ width: '68px', height: '68px', borderRadius: '50%', objectFit: 'cover', flexShrink: 0 }}
          />
        ) : (
          <div style={{
            width: '68px', height: '68px', borderRadius: '50%',
            backgroundColor: '#d1d5db',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '22px', fontWeight: '700', color: '#6b7280', flexShrink: 0,
          }}>
            {initials || 'U'}
          </div>
        )}

        <div style={{ display: 'flex', gap: '12px' }}>
          <button
            onClick={() => fileInputRef.current?.click()}
            style={{
              backgroundColor: '#2563eb', color: 'white', border: 'none',
              borderRadius: '10px', padding: '9px 20px', fontSize: '14px',
              fontWeight: '600', cursor: 'pointer',
            }}
          >
            Upload new
          </button>
          <button
            onClick={handleDeleteAvatar}
            style={{
              backgroundColor: 'white', color: '#2563eb',
              border: '1.5px solid #2563eb', borderRadius: '10px',
              padding: '9px 20px', fontSize: '14px', fontWeight: '600', cursor: 'pointer',
            }}
          >
            Delete
          </button>
        </div>
      </div>

      {/* Personal information card */}
      <div style={{ backgroundColor: 'white', border: '1px solid #e5e7eb', borderRadius: '16px', padding: '24px 28px' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px' }}>
          <p style={{ fontSize: '16px', fontWeight: '700', color: '#2563eb', margin: 0 }}>Personal information</p>
          {editPersonal
            ? saveCancel(savePersonal, () => setEditPersonal(false), savingPersonal)
            : editBtn(() => setEditPersonal(true))}
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
          <Field label="First name" value={userData.first_name} editing={editPersonal}
            onChange={v => setUserData(d => ({ ...d, first_name: v }))} />
          <Field label="Last name" value={userData.last_name} editing={editPersonal}
            onChange={v => setUserData(d => ({ ...d, last_name: v }))} />
          <Field label="Email address" value={userData.email} editing={editPersonal} type="email"
            onChange={v => setUserData(d => ({ ...d, email: v }))} />
          <div style={fieldBox}>
            <p style={fieldLabel}>Organization name</p>
            <p style={fieldValue}>{userData.org_name || '—'}</p>
          </div>
          <div style={fieldBox}>
            <p style={fieldLabel}>Role</p>
            <p style={{ fontSize: '14px', fontWeight: '600', color: '#16a34a', margin: 0, textTransform: 'capitalize' }}>
              {userData.role || '—'}
            </p>
          </div>
        </div>
      </div>


    </div>
  )
}

function Field({
  label, value, editing, onChange, type = 'text',
}: {
  label: string
  value: string
  editing: boolean
  onChange: (v: string) => void
  type?: string
}) {
  if (editing) {
    return (
      <div>
        <p style={{ fontSize: '11px', color: '#6b7280', margin: '0 0 6px' }}>{label}</p>
        <input
          type={type}
          value={value}
          onChange={e => onChange(e.target.value)}
          style={{
            width: '100%',
            backgroundColor: '#f3f4f6',
            border: '1.5px solid #2563eb',
            borderRadius: '10px',
            padding: '10px 14px',
            fontSize: '14px',
            fontWeight: '500',
            color: '#111827',
            outline: 'none',
            boxSizing: 'border-box',
          }}
        />
      </div>
    )
  }
  return (
    <div style={{ backgroundColor: '#f3f4f6', borderRadius: '10px', padding: '10px 14px' }}>
      <p style={{ fontSize: '11px', color: '#9ca3af', margin: '0 0 4px' }}>{label}</p>
      <p style={{ fontSize: '14px', fontWeight: '500', color: '#111827', margin: 0 }}>{value || '—'}</p>
    </div>
  )
}
