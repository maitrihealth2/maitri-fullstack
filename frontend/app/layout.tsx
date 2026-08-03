import type { Metadata } from 'next'
import { Literata } from 'next/font/google'
import Script from 'next/script'
import { Analytics } from '@vercel/analytics/next'
import { Providers } from '@/core/providers'
import BottomNav from '@/shared/components/BottomNav'
import GlobalShortcuts from '@/shared/components/GlobalShortcuts'
import './globals.css'

const literata = Literata({
  subsets: ['latin'],
  variable: '--font-literata',
  display: 'swap',
})

export const metadata: Metadata = {
  title: 'Mythri | Sanctuary',
  description: 'A safe, quiet space for reflection and healing.',
  keywords: 'mental health, AI companion, therapy, support',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light bg-immersive" suppressHydrationWarning>
      <head>
        <link href="https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:wght,FILL@100..700,0..1&display=swap" rel="stylesheet" />
      </head>
      <body className={`${literata.variable} font-body-md antialiased bg-immersive min-h-[100dvh] flex flex-col text-on-background relative md:h-[100dvh] md:overflow-hidden`}>
        {/* Google Analytics */}
        <Script strategy="afterInteractive" src="https://www.googletagmanager.com/gtag/js?id=G-DBD64NEBF5" />
        <Script id="google-analytics" strategy="afterInteractive">
          {`
            window.dataLayer = window.dataLayer || [];
            function gtag(){dataLayer.push(arguments);}
            gtag('js', new Date());
            gtag('config', 'G-DBD64NEBF5');
          `}
        </Script>

        <GlobalShortcuts />

        {/* Background Grain and Ambient Blobs */}
        <div className="bg-grain"></div>
        {/* Desktop Blobs (hidden on small) */}
        <div className="hidden md:block fixed top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-tertiary-fixed/10 opacity-30 pointer-events-none z-0"></div>
        <div className="hidden md:block fixed bottom-[-10%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-secondary-fixed/20 opacity-30 pointer-events-none z-0"></div>
        {/* Mobile Blobs */}
        <div className="block md:hidden fixed top-[-10%] left-[-10%] w-[50vw] h-[50vw] rounded-full bg-slate-300/20 opacity-30 pointer-events-none z-0"></div>
        <div className="block md:hidden fixed bottom-[-10%] right-[-10%] w-[60vw] h-[60vw] rounded-full bg-stone-200/20 opacity-30 pointer-events-none z-0"></div>
        <Providers>
          {children}
        </Providers>
        <BottomNav />
        <Analytics />
      </body>
    </html>
  )
}

