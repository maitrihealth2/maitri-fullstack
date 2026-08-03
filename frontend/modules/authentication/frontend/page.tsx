'use client'
import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { login, register, googleLogin } from '@/core/api'
import { auth, googleProvider, isFirebaseConfigured } from '@/core/firebase'
import { signInWithPopup } from 'firebase/auth'

export default function LoginPage() {
  const router = useRouter()
  const [mode, setMode] = useState<'signin' | 'create'>('signin')
  const [form, setForm] = useState({ name: '', email: '', password: '', confirmPassword: '' })
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)

  useEffect(() => {
    const token = typeof window !== 'undefined' ? localStorage.getItem('mb_token') : null;
    if (token) {
      router.replace('/home');
    }
  }, [router]);

  const handleGoogleLogin = async () => {
    if (!isFirebaseConfigured || !auth || !googleProvider) {
      setError('Google Sign-In is not configured. Please sign in with email and password.')
      return
    }

    try {
      setLoading(true)
      setError('')
      const result = await signInWithPopup(auth, googleProvider)
      const idToken = await result.user.getIdToken()
      const data = await googleLogin(idToken)
      localStorage.setItem('mb_token', data.access_token)
      localStorage.setItem('mb_username', data.username)
      localStorage.setItem('mb_language', 'en-IN')
      document.cookie = `mb_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`
      sessionStorage.removeItem('mb_session_id')
      if (typeof window !== 'undefined' && (window as any).gtag) {
        (window as any).gtag('event', 'login', { method: 'Google' })
      }
      window.location.href = '/home'
    } catch (err: any) {
      console.error("Google Auth Error:", err)
      setError(err?.response?.data?.detail || err.message || "Google Sign-In failed.")
      setLoading(false)
    }
  }

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault()
    if (!form.email.trim() || !form.password.trim() || (mode === 'create' && !form.name.trim())) {
      setError('Please fill in all required fields')
      return
    }
    if (mode === 'create' && form.password !== form.confirmPassword) {
      setError('Passwords do not match')
      return
    }
    
    setError('')
    setLoading(true)
    try {
      const data = mode === 'signin'
        ? await login(form.email, form.password)
        : await register(form.name, form.email, form.password, 'en-IN')
        
      localStorage.setItem('mb_token', data.access_token)
      localStorage.setItem('mb_username', data.username)
      localStorage.setItem('mb_language', 'en-IN')
      document.cookie = `mb_token=${data.access_token}; path=/; max-age=86400; SameSite=Lax`
      sessionStorage.removeItem('mb_session_id')
      window.location.href = '/home' // Force hard redirect to dashboard
    } catch (err: any) {
      console.error("API Error:", err)
      setError(err?.response?.data?.detail || err.message || "Something didn't quite work. Please check your details.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 w-full flex items-center justify-center relative overflow-hidden">
      {/* Video Backgrounds */}
      <video autoPlay loop muted playsInline className="hidden md:block fixed inset-0 w-full h-full object-cover z-0 pointer-events-none">
          <source src="/desktop_bg.webm" type="video/webm" />
      </video>
      <video autoPlay loop muted playsInline className="block md:hidden fixed inset-0 w-full h-full object-cover z-0 pointer-events-none">
          <source src="/mobile_bg.webm" type="video/webm" />
      </video>
      
      {/* Overlay for better contrast */}
      <div className="fixed inset-0 bg-plum-high-contrast/10 backdrop-blur-[2px] z-0 pointer-events-none"></div>
      
      {/* Main Authentication Container */}
      <main className="relative z-10 w-full max-w-[440px] m-auto px-margin-mobile animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
          <div className="frosted-card rounded-3xl px-8 py-6 md:px-10 md:py-8 flex flex-col items-center space-y-5">
              
              {/* Brand Identity */}
              <div className="text-center">
                  <h1 className="text-plum-high-contrast font-display-lg text-4xl md:text-5xl mb-1">Mythri</h1>
                  <p className="text-on-surface-variant font-body-md text-sm md:text-base italic opacity-90">A digital sanctuary for the mind.</p>
              </div>

              {/* Step 1: Auth Container */}
              <div id="authStep" className="w-full space-y-5 transition-all duration-500">
                  {/* Tab Switcher */}
                  <div className="relative w-full flex border-b border-outline-variant/30">
                      <button
                          className={`flex-1 py-3 text-center font-label-md text-sm transition-colors ${mode === 'signin' ? 'text-plum-high-contrast' : 'text-on-surface-variant/70 hover:text-plum-high-contrast'}`}
                          onClick={() => { setMode('signin'); setError(''); }}
                          type="button">
                          Sign in
                      </button>
                      <button
                          className={`flex-1 py-3 text-center font-label-md text-sm transition-colors ${mode === 'create' ? 'text-plum-high-contrast' : 'text-on-surface-variant/70 hover:text-plum-high-contrast'}`}
                          onClick={() => { setMode('create'); setError(''); }}
                          type="button">
                          Create account
                      </button>
                      {/* Active Underline */}
                      <div className="absolute bottom-0 left-0 w-1/2 h-0.5 bg-plum-high-contrast tab-underline transition-transform duration-300"
                          style={{ transform: mode === 'signin' ? 'translateX(0%)' : 'translateX(100%)' }}></div>
                  </div>

                  {/* Auth Form */}
                  <form className="w-full space-y-4" onSubmit={handleSubmit}>
                      {/* Welcome Message (Dynamic) */}
                      <div className="mb-2 text-center space-y-1">
                          <h2 className="text-plum-high-contrast font-headline-md text-2xl">
                              {mode === 'signin' ? 'Welcome back' : 'Join our sanctuary'}
                          </h2>
                          <p className="text-on-surface-variant font-body-sm text-sm">
                              {mode === 'signin' ? 'Please enter your credentials to continue.' : 'Begin your journey toward quiet reflection.'}
                          </p>
                      </div>

                      {/* Name Field (Hidden for Sign In) */}
                      {mode === 'create' && (
                          <div className="space-y-1.5 animate-fade-up">
                              <label className="block font-label-md text-sm text-plum-high-contrast ml-1" htmlFor="name">Full name</label>
                              <input
                                  className="w-full h-12 px-5 rounded-2xl border border-outline-variant/30 bg-white/40 font-body-md placeholder:text-outline/40 focus:bg-white/80 transition-all outline-none"
                                  id="name" placeholder="John Doe" type="text"
                                  value={form.name} onChange={e => setForm({ ...form, name: e.target.value })}
                                  required
                              />
                          </div>
                      )}

                      {/* Email Field */}
                      <div className="space-y-1.5">
                          <label className="block font-label-md text-sm text-plum-high-contrast ml-1" htmlFor="email">Email address</label>
                          <input
                              className="w-full h-12 px-5 rounded-2xl border border-outline-variant/30 bg-white/40 font-body-md placeholder:text-outline/40 focus:bg-white/80 transition-all outline-none"
                              id="email" placeholder="name@example.com" required type="email"
                              value={form.email} onChange={e => setForm({ ...form, email: e.target.value })}
                          />
                      </div>

                      <div className="flex gap-4 w-full">
                          {/* Password Field */}
                          <div className="space-y-1.5 relative flex-1">
                              <div className="flex justify-between items-center px-1">
                                  <label className="font-label-md text-sm text-plum-high-contrast" htmlFor="password">Password</label>
                                  {mode === 'signin' && (
                                      <a className="font-label-md text-primary/70 hover:text-plum-high-contrast transition-colors text-xs" href="#">Forgot?</a>
                                  )}
                              </div>
                              <div className="relative">
                                  <input
                                      className="w-full h-12 px-5 rounded-2xl border border-outline-variant/30 bg-white/40 font-body-md placeholder:text-outline/40 focus:bg-white/80 transition-all outline-none"
                                      id="password" placeholder="••••••••" required type={showPassword ? 'text' : 'password'}
                                      value={form.password} onChange={e => setForm({ ...form, password: e.target.value })}
                                  />
                                  <button
                                      className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant/50 hover:text-plum-high-contrast transition-colors flex items-center"
                                      onClick={() => setShowPassword(!showPassword)} type="button">
                                      <span className="material-symbols-outlined text-[18px]">{showPassword ? 'visibility_off' : 'visibility'}</span>
                                  </button>
                              </div>
                          </div>

                          {/* Confirm Password Field (Hidden for Sign In) */}
                          {mode === 'create' && (
                              <div className="space-y-1.5 relative flex-1 animate-fade-up">
                                  <div className="flex justify-between items-center px-1">
                                      <label className="font-label-md text-sm text-plum-high-contrast" htmlFor="confirmPassword">Confirm</label>
                                  </div>
                                  <div className="relative">
                                      <input
                                          className="w-full h-12 px-5 rounded-2xl border border-outline-variant/30 bg-white/40 font-body-md placeholder:text-outline/40 focus:bg-white/80 transition-all outline-none"
                                          id="confirmPassword" placeholder="••••••••" required type={showConfirmPassword ? 'text' : 'password'}
                                          value={form.confirmPassword} onChange={e => setForm({ ...form, confirmPassword: e.target.value })}
                                      />
                                      <button
                                          className="absolute right-4 top-1/2 -translate-y-1/2 text-on-surface-variant/50 hover:text-plum-high-contrast transition-colors flex items-center"
                                          onClick={() => setShowConfirmPassword(!showConfirmPassword)} type="button">
                                          <span className="material-symbols-outlined text-[18px]">{showConfirmPassword ? 'visibility_off' : 'visibility'}</span>
                                      </button>
                                  </div>
                              </div>
                          )}
                      </div>

                      {/* Error Message */}
                      {error && (
                          <div className="py-3 px-4 bg-error-container/80 backdrop-blur-sm text-on-error-container rounded-xl font-body-sm text-sm flex items-center gap-3">
                              <span className="material-symbols-outlined text-[18px]">info</span>
                              <span>{error}</span>
                          </div>
                      )}

                      {/* Submit Button */}
                      <button
                          className="w-full h-12 bg-plum-high-contrast text-white font-label-md text-sm rounded-2xl hover:opacity-90 active:scale-[0.98] transition-all flex justify-center items-center gap-2 shadow-xl shadow-plum-high-contrast/20 disabled:opacity-50"
                          type="submit" disabled={loading}>
                          <span>{loading ? 'Processing...' : (mode === 'signin' ? 'Continue to Sanctuary' : 'Create Account')}</span>
                          {!loading && <span className="material-symbols-outlined text-[18px]">arrow_forward</span>}
                      </button>
                  </form>

                  {/* Social/Other Methods */}
                  <div className="w-full animate-fade-up">
                      <div className="flex items-center gap-4 mb-3">
                          <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                          <span className="font-label-md text-[10px] text-outline/50 uppercase tracking-widest">or</span>
                          <div className="h-[1px] flex-1 bg-outline-variant/20"></div>
                      </div>
                      <button
                          className={`w-full h-12 border border-outline-variant/30 bg-white/20 text-plum-high-contrast font-label-md text-sm rounded-2xl transition-colors flex justify-center items-center gap-3 ${!isFirebaseConfigured ? 'opacity-40 cursor-not-allowed hover:bg-white/20' : 'hover:bg-white/40'}`}
                          type="button" onClick={handleGoogleLogin}
                          disabled={!isFirebaseConfigured}>
                          <svg className="w-5 h-5" viewBox="0 0 24 24">
                              <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"></path>
                              <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"></path>
                              <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"></path>
                              <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"></path>
                          </svg>
                          Continue with Google
                      </button>
                      {!isFirebaseConfigured && (
                        <p className="text-xs text-on-surface-variant mt-2">
                          Firebase Google Sign-In is unavailable until the Firebase environment is configured.
                        </p>
                      )}
                  </div>
              </div>
          </div>
      </main>
    </div>
  )
}
