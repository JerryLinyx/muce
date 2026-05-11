import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import { QueryProvider } from '@/components/providers/QueryProvider'
import { TopBar } from '@/components/topbar/TopBar'
import './globals.css'

const inter = Inter({ subsets: ['latin'], display: 'swap', variable: '--font-inter' })

export const metadata: Metadata = {
  title: 'Muce 牧策',
  description: 'A 股多因子研究终端',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="zh-CN" className={inter.variable}>
      <body>
        <QueryProvider>
          <TopBar />
          <main className="min-h-[calc(100vh-44px)]">{children}</main>
        </QueryProvider>
      </body>
    </html>
  )
}
