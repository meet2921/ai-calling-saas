import { NextRequest, NextResponse } from 'next/server'

const PUBLIC_ROUTES = ['/login', '/forgot-password', '/reset-password']

export function middleware(request: NextRequest) {
  const { pathname } = request.nextUrl
  const token = request.cookies.get('access_token')?.value

  if (PUBLIC_ROUTES.some((r) => pathname.startsWith(r))) {
    return NextResponse.next()
  }

  if (!token) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  const role = request.cookies.get('user_role')?.value
  if (pathname.startsWith('/superadmin') && role !== 'super_admin') {
    return NextResponse.redirect(new URL('/dashboard', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: ['/((?!_next/static|_next/image|favicon.ico|public|logo.png|.*\\.png|.*\\.jpg|.*\\.svg|.*\\.ico).*)'],
}
