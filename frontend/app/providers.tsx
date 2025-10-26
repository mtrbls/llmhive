'use client'

import { WalletProvider } from '@/lib/WalletContext'
import React from 'react'

export function Providers({ children }: { children: React.ReactNode }) {
  return <WalletProvider>{children}</WalletProvider>
}
