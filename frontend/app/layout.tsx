import type { Metadata } from 'next'
import './globals.css'
import { Providers } from '@/app/providers'
import { Sidebar } from '@/components/Sidebar'
import { WalletButton } from '@/components/WalletButton'

export const metadata: Metadata = {
  title: 'LLM Hive - Distributed AI Inference',
  description: 'Run distributed AI inference with automatic payments',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="bg-gray-50">
        <Providers>
          <div className="min-h-screen bg-white flex flex-col">
            {/* Header */}
            <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
              <div className="w-4/5 mx-auto flex items-center justify-between">
                <div>
                  <h1 className="text-3xl font-bold text-gray-900">LLM Hive</h1>
                  <p className="text-gray-600 text-sm">Distributed AI Inference with Concordium Payments</p>
                </div>
                <WalletButton />
              </div>
            </div>

            {/* Main Content */}
            <div className="flex-1 flex overflow-hidden w-4/5 mx-auto">
              <Sidebar />
              {children}
            </div>
          </div>
        </Providers>
      </body>
    </html>
  )
}
