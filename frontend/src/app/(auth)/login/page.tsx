'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { Eye, EyeOff, Loader2, AlertCircle } from 'lucide-react'
import { authApi } from '@/lib/api/auth'
import { useAuthStore } from '@/store/auth.store'

const loginSchema = z.object({
  org_slug: z.string().min(1, 'Organization slug is required'),
  email: z.string().email('Invalid email format'),
  password: z.string().min(1, 'Password is required'),
})

type LoginForm = z.infer<typeof loginSchema>

export default function LoginPage() {
  const router = useRouter()
  const { setUser, setTokens } = useAuthStore()
  const [showPassword, setShowPassword] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginForm) => {
    setLoading(true)
    setError('')
    try {
      const loginRes = await authApi.login(data)
      const { access_token, refresh_token } = loginRes.data
      setTokens(access_token, refresh_token)

      const meRes = await authApi.me()
      const user = meRes.data
      setUser(user)

      document.cookie = `access_token=${access_token}; path=/`
      document.cookie = `user_role=${user.role}; path=/`

      if (user.role === 'super_admin') {
        router.push('/superadmin')
      } else {
        router.push('/dashboard')
      }
    } catch (err: any) {
      const detail = err?.response?.data?.detail
      if (detail === 'Account is inactive. Contact your admin.') {
        setError('Your account is inactive. Contact your administrator.')
      } else {
        setError('Invalid email or password. Please check your credentials and try again.')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ backgroundColor: '#e8edf2' }}
    >
      <div className="w-full max-w-sm" >
        <div
          className="bg-white "
          style={{ borderRadius: '24px',
            border: '1.5px solid #1a1a2e20', 
            boxShadow: '0 4px 32px 0 rgba(0,0,0,0.10)', 
            padding: '25px 36px' }}
        >
          {/* Logo */}
          <div className="flex flex-col items-center" style={{ marginBottom: '24px' }}>
            <div className="mb-4">
              <img
                src="/logo.png"
                alt="TierceIndia Logo"
                style={{ height: '52px', width: 'auto', borderRadius: '12px' }}
              />
            </div>
            <h1 className="text-xl font-bold text-gray-900 text-center whitespace-nowrap">
              AI-Powered Calling, Simplified
            </h1>
            <p className="text-sm text-gray-400 mt-1">Sign in to your account</p>
          </div>

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-6 py-10">



            {/* Organisation slug */}
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-2.5">
                Organisation slug
              </label>
              <input
                {...register('org_slug')}
                type="text"
                placeholder="example-org"
                disabled={loading}
                className="w-full px-4 py-3 text-sm text-gray-800 placeholder-gray-400 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-blue-400"
                style={{

                  backgroundColor: '#f5f7fa',
                  border: '1.5px solid #e5e9ef',
                  borderRadius: '12px',
                  padding: '10px 14px',
                  margin: '3px 0',
                }}
              />
              {errors.org_slug && (
                <p className="mt-1 text-xs text-red-500">{errors.org_slug.message}</p>
              )}
            </div>

            {/* Email */}
            <div>
              <label
                className="block text-sm font-semibold mb-2.5"
                style={{ color: errors.email ? '#ef4444' : '#1f2937' }}
              > 
                Email
              </label>
              <input
                {...register('email')}
                type="email"
                placeholder="name@company.com"
                disabled={loading}
                className="w-full px-4 py-3.5 text-sm text-gray-800 placeholder-gray-400 disabled:opacity-60 focus:outline-none focus:ring-2"
                style={{
                  backgroundColor: '#f5f7fa',
                  border: `1.5px solid ${errors.email ? '#f87171' : '#e5e9ef'}`,
                  borderRadius: '12px',
                  outline: 'none',
                  padding: '10px 14px',
                  margin: '3px 0'
                }}
              />
              {errors.email && (
                <p className="mt-1 text-xs text-red-500">{errors.email.message}</p>
              )}
            </div>

            {/* Password */}
            <div>
              <label className="block text-sm font-semibold text-gray-800 mb-2.5">
                Password
              </label>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  placeholder="••••••••"
                  disabled={loading}
                  className="w-full px-4 py-3 pr-12 text-sm text-gray-800 placeholder-gray-400 disabled:opacity-60 focus:outline-none focus:ring-2 focus:ring-blue-400"
                  style={{
                    backgroundColor: '#f5f7fa',
                    border: '1.5px solid #e5e9ef',
                    borderRadius: '12px',
                    padding: '10px 14px',
                    margin: '3px 0'
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4
                   top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  style={{
                    padding:'4px 8px',
                }}
                  tabIndex={-1}
                >
                  {showPassword
                    ? <Eye className="w-4 h-4" />
                    : <EyeOff className="w-4 h-4" />
                  }
                </button>
              </div>
              {errors.password && (
                <p className="mt-1 text-xs text-red-500">{errors.password.message}</p>
              )}
              <div className="flex justify-end mt-2">
                <a
                  href="/forgot-password"
                  className="text-xs font-medium text-blue-500 hover:text-blue-600"
                >
                  Forgot Password?
                </a>
              </div>
            </div>

            {/* Inline error banner */}
            {error && (
              <div
                className="flex items-start gap-2.5 px-4 py-3"
                style={{
                  backgroundColor: '#fef2f2',
                  border: '1px solid #fecaca',
                  borderRadius: '10px',
                }}
              >
                <AlertCircle className="w-4 h-4 mt-0.5 shrink-0 text-red-500" />
                <p className="text-xs text-red-700 leading-relaxed">
                  <span className="font-semibold">Invalid email or password.</span>
                  <br />
                  Please check your credentials and try again.
                </p>
              </div>
            )}

            {/* Submit button */}
            <button
              type="submit"
              disabled={loading}
            className="w-full py-4 text-base font-semibold text-white transition-all flex items-center justify-center gap-2 disabled:cursor-not-allowed"           
               style={{
                backgroundColor: loading ? '#93c5fd' : '#4F8EF7',
                borderRadius: '10px',
                color: loading ? '#bfdbfe' : 'white',
                padding: '15px 0',
                marginTop: '25px',
              }}
            >
              {loading
                ? <><Loader2 className="w-4 h-4 animate-spin" />Signing in...</>
                : 'Sign in'
              }
            </button>

          </form>
        </div>
      </div>
    </div>
  )
}