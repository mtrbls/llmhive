'use client'

import React, { createContext, useState, useCallback, useEffect } from 'react'

export interface WalletContextType {
  account: string | null
  isConnected: boolean
  isConnecting: boolean
  connectWallet: () => Promise<void>
  disconnectWallet: () => void
  sendPayment: (recipient: string, amountCCD: number) => Promise<string>
  error: string | null
}

export const WalletContext = createContext<WalletContextType | undefined>(
  undefined
)

export function WalletProvider({ children }: { children: React.ReactNode }) {
  const [account, setAccount] = useState<string | null>(null)
  const [isConnecting, setIsConnecting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const connectWallet = useCallback(async () => {
    try {
      setIsConnecting(true)
      setError(null)

      if (!window.concordium) {
        throw new Error(
          'Concordium wallet not found. Please install the Concordium Browser Wallet extension.'
        )
      }

      const accounts = await window.concordium.requestAccounts()
      if (accounts && accounts.length > 0) {
        setAccount(accounts[0])
        console.log('Wallet connected:', accounts[0])
      } else {
        throw new Error('No accounts found')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Unknown error'
      setError(message)
      console.error('Wallet connection error:', err)
    } finally {
      setIsConnecting(false)
    }
  }, [])

  const disconnectWallet = useCallback(() => {
    setAccount(null)
    setError(null)
  }, [])

  const sendPayment = useCallback(
    async (recipient: string, amountCCD: number): Promise<string> => {
      if (!account) {
        throw new Error('Wallet not connected')
      }

      if (!window.concordium) {
        throw new Error('Wallet extension not available')
      }

      try {
        const amountMicroCCD = BigInt(Math.round(amountCCD * 1000000))

        const txHash = await window.concordium.sendTransaction(
          0, // SimpleTransfer
          {
            toAddress: recipient,
            amount: amountMicroCCD,
          }
        )

        console.log('Payment sent:', txHash)
        return txHash
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Payment failed'
        setError(message)
        throw err
      }
    },
    [account]
  )

  useEffect(() => {
    // Listen for account changes
    if (window.concordium && window.concordium.on) {
      window.concordium.on('accountChanged', (newAccount: string) => {
        setAccount(newAccount)
      })
    }
  }, [])

  return (
    <WalletContext.Provider
      value={{
        account,
        isConnected: !!account,
        isConnecting,
        connectWallet,
        disconnectWallet,
        sendPayment,
        error,
      }}
    >
      {children}
    </WalletContext.Provider>
  )
}

export function useWallet() {
  const context = React.useContext(WalletContext)
  if (!context) {
    throw new Error('useWallet must be used within WalletProvider')
  }
  return context
}

// Extend window interface for TypeScript
declare global {
  interface Window {
    concordium: any
  }
}
