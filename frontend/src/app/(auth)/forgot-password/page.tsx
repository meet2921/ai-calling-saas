'use client'

import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { KeyRound, Loader2, CheckCircle2, WifiOff } from 'lucide-react'
import { authApi } from '@/lib/api/auth'

const schema = z.object({
  org_slug: z.string().min(1, 'Organization slug is required'),
  email: z.string().email('Invalid email address'),
})

type FormData = z.infer<typeof schema>
type PageState = 'idle' | 'loading' | 'success' | 'error'

export default function ForgotPasswordPage() {
  const [pageState, setPageState] = useState<PageState>('idle')
  const [submittedEmail, setSubmittedEmail] = useState('')

  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
  })

  const onSubmit = async (data: FormData) => {
    setPageState('loading')
    try {
      await authApi.forgotPassword({ org_slug: data.org_slug, email: data.email })
      setSubmittedEmail(data.email)
      setPageState('success')
    } catch {
      setPageState('error')
    }
  }

  return (
    <div
      className="min-h-screen flex items-center justify-center p-6"
      style={{ backgroundColor: '#eef1f5' }}
    >
      <div className="w-full max-w-sm" style={{ maxWidth: '380px' }}>
        <div
          className="bg-white"
          style={{
            borderRadius: '24px',
            border: '1.5px solid #e5e7eb',
            boxShadow: '0 4px 24px rgba(0,0,0,0.08)',
            padding: '25px 36px',
          }}     
        >

          {/* SUCCESS */}
          {pageState === 'success' && (
            <div className="flex flex-col items-center text-center">
              <div
                className="flex items-center justify-center mb-4"
                style={{
                  width: '56px', height: '56px',
                  backgroundColor: '#dcfce7',
                  borderRadius: '16px',
                }}
              >
                <CheckCircle2 className="w-7 h-7 text-green-500" />
              </div>
              <h2 className="font-bold text-gray-900 mb-2" style={{ fontSize: '18px', marginBottom: '5px' }}>
                Check Your e-mail
              </h2>
              <p className="text-gray-500 mb-1" style={{ fontSize: '14px' }}>
                We&apos;ve sent a password reset link to
              </p>
              <p className="font-semibold text-gray-800 mb-4" style={{ fontSize: '14px' }}>
                {submittedEmail}
              </p>
              <p className="text-gray-400 mb-5" style={{ fontSize: '14px', marginBottom: '20px' }}>
                Didn&apos;t receive the e-mail?{' '}
                <button
                  onClick={() => setPageState('idle')}
                  className="text-blue-500 hover:text-blue-600 font-medium"
                >
                  send again
                </button>
              </p>
              <a
                href="https://mail.google.com"
                target="_blank"
                rel="noreferrer"
                className="w-full flex items-center justify-center gap-2.5 mb-5"
                style={{
                  padding: '13px',
                  borderRadius: '10px',
                  border: '1.5px solid #e5e7eb',
                  fontSize: '14px',
                  fontWeight: '500',
                  color: '#374151',
                  marginBottom: '20px',
                }}
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Open Gmail
              </a>
              <p className="text-gray-400" style={{ fontSize: '13px' }}>
                Remember your password?{' '}
                <a href="/login" className="text-blue-500 hover:text-blue-600 font-medium">log in</a>
              </p>
            </div>
          )}

          {/* ERROR */}
          {pageState === 'error' && (
            <div className="flex flex-col items-center text-center">
              <div
                className="flex items-center justify-center mb-4"
                style={{
                  width: '56px', height: '56px',
                  backgroundColor: '#fee2e2',
                  borderRadius: '16px',
                }}
              >
                <WifiOff className="w-7 h-7 text-red-500" />
              </div>
              <h2 className="font-bold text-gray-900 mb-2" style={{ fontSize: '18px',marginBottom: '5px' }}>
                Something went wrong
              </h2>
              <p className="text-gray-400 mb-6 leading-relaxed" style={{ fontSize: '14px', marginBottom: '20px' }}>
                We&apos;re having trouble processing your request right now.
                <br />Please try again in a few moments.
              </p>
              <button
                onClick={() => setPageState('idle')}
                className="w-full text-white font-semibold mb-4"
                style={{
                  backgroundColor: '#4F8EF7',
                  borderRadius: '10px',
                  padding: '14px',
                  fontSize: '15px',
                    marginBottom: '20px',
                }}
              >
                Please try again
              </button>
              <p className="text-gray-400" style={{ fontSize: '13px' }}>
                Remember your password?{' '}
                <a href="/login" className="text-blue-500 hover:text-blue-600 font-medium">log in</a>
              </p>
            </div>
          )}

          {/* FORM */}
          {(pageState === 'idle' || pageState === 'loading') && (
            <>
              <div className="flex flex-col items-center text-center mb-6">
                <div
                  className="flex items-center justify-center mb-4"
                  style={{
                    width: '56px', height: '56px',
                    backgroundColor: '#eff6ff',
                    borderRadius: '16px',
                  }}
                >
                  <KeyRound className="w-6 h-6 text-blue-500" />
                </div>
                <h2 className="font-bold text-gray-900 mb-2" style={{ fontSize: '20px' }}>
                  Forgot password?
                </h2>
                <p className="text-gray-800" style={{ fontSize: '14px' }}>
                  Enter your email address
                </p>
                <p className="text-gray-400" style={{ fontSize: '14px' }}>
                  and we&apos;ll send you a link to reset your password.
                </p>
              </div>

              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                <div>
                  <label className="block font-semibold text-gray-800 mb-2" style={{ fontSize: '14px',marginTop:'10px', marginBottom:'5px' }}>
                    Organisation slug
                  </label>
                  <input
                    {...register('org_slug')}
                    type="text"
                    placeholder="example-org"
                    disabled={pageState === 'loading'}
                    className="w-full focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-60"
                    style={{
                      backgroundColor: '#f3f6fb',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '12px 16px',
                      fontSize: '14px',
                      color: '#374151',
                    }}

                  />
                  {errors.org_slug && (
                    <p className="mt-1 text-red-500" style={{ fontSize: '12px' }}>
                      {errors.org_slug.message}
                    </p>
                  )}
                </div>
                  <div>
                  <label className="block font-semibold text-gray-800 mb-2" style={{ fontSize: '14px', marginTop:'10px' }}>
                    Email
                  </label>
                  <input
                    {...register('email')}
                    type="email"
                    placeholder="name@company.com"
                    disabled={pageState === 'loading'}
                    className="w-full focus:outline-none focus:ring-2 focus:ring-blue-400 disabled:opacity-60"
                    style={{
                      backgroundColor: '#f3f6fb',
                      border: 'none',
                      borderRadius: '12px',
                      padding: '12px 16px',
                      fontSize: '14px',
                      color: '#374151',
                    marginBottom: '10px',
                    }}
                  />
                  {errors.email && (
                    <p className="mt-1 text-red-500" style={{ fontSize: '12px' }}>
                      {errors.email.message}
                    </p>
                  )}
                </div>

                <button
                  type="submit"
                  disabled={pageState === 'loading'}
                  className="w-full font-semibold flex items-center justify-center gap-2 disabled:cursor-not-allowed"
                  style={{
                    backgroundColor: pageState === 'loading' ? '#bfdbfe' : '#4F8EF7',
                    color: pageState === 'loading' ? '#3b82f6' : 'white',
                    borderRadius: '10px',
                    padding: '15px 0',
                    fontSize: '15px',
                    marginTop: '20px',
                  }}
                >
                  {pageState === 'loading'
                    ? <><Loader2 className="w-4 h-4 animate-spin" />Sending reset link...</>
                    : 'Send reset link'
                  }
                </button>

                <p className="text-center text-gray-400" style={{ fontSize: '13px', marginTop: '15px' }}>
                  Remember your password?{' '}
                  <a href="/login" className="text-blue-500 hover:text-blue-600 font-medium">Sign in</a>
                </p>
              </form>
            </>
          )}

        </div>
      </div>
    </div>
  )
}