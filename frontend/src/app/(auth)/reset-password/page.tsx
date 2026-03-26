'use client'

import { useState, Suspense } from 'react'
import { useRouter, useSearchParams } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, LockKeyhole, Loader2, WifiOff } from 'lucide-react'
import { authApi } from '@/lib/api/auth'

const schema = z.object({
  new_password: z
    .string()
    .min(8, 'At least 8 characters')
    .regex(/[A-Z]/, 'One uppercase letter required')
    .regex(/[a-z]/, 'One lowercase letter required')
    .regex(/[0-9]/, 'One number required')
    .regex(/[\W_]/, 'One special character required'),
  confirm_password: z.string().min(1, 'Please confirm your password'),
}).refine((d) => d.new_password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
})

type FormData = z.infer<typeof schema>

function ResetForm() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const token = searchParams.get('token')

  const [loading, setLoading]         = useState(false)
  const [showNew, setShowNew]         = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [failed, setFailed]           = useState(false)

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    if (!token) return
    setLoading(true)
    try {
      await authApi.resetPassword({ reset_token: token, new_password: data.new_password })
      router.push('/login')
    } catch {
      setFailed(true)
    } finally {
      setLoading(false)
    }
  }

  // Error state
  if (failed) {
    return (
      <div className="flex flex-col items-center text-center">
        <div
          className="flex items-center justify-center mb-4"
          style={{ width: '56px', height: '56px', backgroundColor: '#fee2e2', borderRadius: '16px' }}
        >
          <WifiOff className="w-6 h-6 text-red-500" />
        </div>
        <h2 className="font-bold text-gray-900 mb-2" style={{ fontSize: '18px', marginBottom: '5px' }}>
          Something went wrong
        </h2>
        <p className="text-gray-400 mb-6 leading-relaxed" style={{ fontSize: '14px', marginBottom: '20px' }}>
          We&apos;re having trouble processing your request right now.
          <br />Please try again in a few moments.
        </p>
        <button
          onClick={() => setFailed(false)}
          className="w-full text-white font-semibold mb-4"
          style={{ backgroundColor: '#4F8EF7', 
            borderRadius: '10px',
             padding: '14px',
              fontSize: '15px',
              marginBottom: '20px'
            }}
        >
          Please try again
        </button>
        <p className="text-gray-400" style={{ fontSize: '13px' }}>
          Remember your password?{' '}
          <a href="/login" className="text-blue-500 font-medium">log in</a>
        </p>
      </div>
    )
  }

  // No token state
  if (!token) {
    return (
      <div className="flex flex-col items-center text-center">
        <div
          className="flex items-center justify-center mb-4"
          style={{ width: '56px', height: '56px', backgroundColor: '#fee2e2', borderRadius: '16px' }}
        >
          <LockKeyhole className="w-6 h-6 text-red-500" />
        </div>
        <h2 className="font-bold text-gray-900 mb-2" style={{ fontSize: '18px' , marginBottom: '5px' }}>
          Link expired
        </h2>
        <p className="text-gray-400 mb-6" style={{ fontSize: '14px', marginBottom: '20px' }}>
          This reset link is invalid or has expired.
        </p>
        <a
          href="/forgot-password"
          className="w-full block text-center text-white font-semibold"
          style={{ backgroundColor: '#4F8EF7', borderRadius: '10px', padding: '14px', fontSize: '15px' }}
        >
          Request a new link
        </a>
      </div>
    )
  }

  // Form state
  return (
    <>
      <div className="flex flex-col items-center text-center mb-6">
        <div
          className="flex items-center justify-center mb-4"
          style={{ width: '56px', height: '56px', backgroundColor: '#eff6ff', borderRadius: '16px' }}
        >
          <LockKeyhole className="w-6 h-6 text-blue-500" />
        </div>
        <h2 className="font-bold text-gray-900" style={{ fontSize: '20px', marginBottom: '15px' }}>
          Set a new password
        </h2>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">

        <div>
          <label className="block font-semibold text-gray-800 mb-2" style={{ fontSize: '14px', marginBottom: '5px' }}>
            New Password
          </label>
          <div className="relative">
            <input
              {...register('new_password')}
              type={showNew ? 'text' : 'password'}
              placeholder="••••••••"
              disabled={loading}
              className="w-full focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-60"
              style={{
                backgroundColor: '#f3f6fb',
                border: 'none',
                borderRadius: '12px',
                padding: '12px 44px 12px 16px',
                fontSize: '14px',
                color: '#374151',
                width: '100%',
                marginBottom: '10px',
              }}
            />
            <button
              type="button"
              onClick={() => setShowNew(!showNew)}
              className="absolute top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              style={{ right: '14px' }}
              tabIndex={-1}
            >
              {showNew ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
          </div>
          {errors.new_password && (
            <p className="mt-1 text-red-500" style={{ fontSize: '12px' }}>{errors.new_password.message}</p>
          )}
        </div>

        <div>
          <label className="block font-semibold text-gray-800 mb-2" style={{ fontSize: '14px', marginBottom: '5px' }}>
            Confirm Password
          </label>
          <div className="relative">
            <input
              {...register('confirm_password')}
              type={showConfirm ? 'text' : 'password'}
              placeholder="••••••••"
              disabled={loading}
              className="w-full focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-60"
              style={{
                backgroundColor: '#f3f6fb',
                border: 'none',
                borderRadius: '12px',
                padding: '12px 44px 12px 16px',
                fontSize: '14px',
                color: '#374151',
                width: '100%',
                marginBottom: '10px',
              }}
            />
            <button
              type="button"
              onClick={() => setShowConfirm(!showConfirm)}
              className="absolute top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
              style={{ right: '14px' }}
              tabIndex={-1}
            >
              {showConfirm ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
            </button>
          </div>
          {errors.confirm_password && (
            <p className="mt-1 text-red-500" style={{ fontSize: '12px' }}>{errors.confirm_password.message}</p>
          )}
        </div>

        <button
          type="submit"
          disabled={loading}
          className="w-full font-semibold text-white flex items-center justify-center gap-2 disabled:cursor-not-allowed"
          style={{
            backgroundColor: loading ? '#bfdbfe' : '#4F8EF7',
            color: loading ? '#3b82f6' : 'white',
            borderRadius: '10px',
            padding: '14px',
            fontSize: '15px',
            marginTop: '20px',
          }}
        >
          {loading
            ? <><Loader2 className="w-4 h-4 animate-spin" />Updating...</>
            : 'Update password'
          }
        </button>

      </form>
    </>
  )
}

export default function ResetPasswordPage() {
  return (
    <div
      className="min-h-screen flex items-center justify-center p-4"
      style={{ backgroundColor: '#eef1f5' }}
    >
      <div className="w-full" style={{ maxWidth: '380px' }}>
        <div
          className="bg-white"
          style={{
            borderRadius: '24px',
            border: '1.5px solid #e5e7eb',
            boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
            padding: '36px 32px',
          }}
        >
          <Suspense fallback={
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          }>
            <ResetForm />
          </Suspense>
        </div>
      </div>
    </div>
  )
}