import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import { User } from '@/types'

interface AuthStore {
  user: User | null
  isAuthenticated: boolean
  setUser: (user: User) => void
  setTokens: (access: string, refresh: string) => void
  clearAuth: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set) => ({
      user: null,
      isAuthenticated: false,

      setUser: (user) => {
        set({ user, isAuthenticated: true })
        if (typeof window !== 'undefined') {
          const secure = location.protocol === 'https:' ? '; Secure' : ''
          document.cookie = `user_role=${user.role}; path=/; max-age=86400; SameSite=Strict${secure}`
        }
      },

      setTokens: (_access, refresh) => {
        if (typeof window !== 'undefined') {
          // Access token is in HttpOnly cookie set by the server — not stored here.
          // Refresh token kept in localStorage only for the token-refresh API call body.
          localStorage.setItem('refresh_token', refresh)
        }
      },

      clearAuth: () => {
        if (typeof window !== 'undefined') {
          localStorage.removeItem('refresh_token')
          document.cookie = 'user_role=; path=/; max-age=0'
        }
        set({ user: null, isAuthenticated: false })
      },
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({ user: state.user, isAuthenticated: state.isAuthenticated }),
    }
  )
)