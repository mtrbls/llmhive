'use client'

import React, { createContext, useState, useCallback, useEffect } from 'react'
import { detectConcordiumProvider } from '@concordium/browser-wallet-api-helpers'
import {
  AccountTransactionType,
  CcdAmount,
  AccountAddress
} from '@concordium/web-sdk'

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
  const [provider, setProvider] = useState<any>(null)

  const connectWallet = useCallback(async () => {
    try {
      setIsConnecting(true)
      setError(null)

      // Use official Concordium provider detection
      const detectedProvider = await detectConcordiumProvider()

      if (!detectedProvider) {
        throw new Error(
          'Concordium wallet not found. Please install the Concordium Browser Wallet extension.'
        )
      }

      // Connect to the wallet
      const accountAddress = await detectedProvider.connect()

      if (accountAddress) {
        setAccount(accountAddress)
        setProvider(detectedProvider)
        console.log('Wallet connected:', accountAddress)
      } else {
        throw new Error('Failed to connect to wallet')
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

      if (!provider) {
        throw new Error('Wallet provider not available. Please reconnect your wallet.')
      }

      try {
        // Convert to microCCD as a simple number
        const amountMicroCCD = Math.floor(amountCCD * 1000000)

        console.log('Attempting payment with:', { account, recipient, amountCCD, amountMicroCCD })

        // Use proper Concordium SDK types for the transaction
        // Wrap addresses in AccountAddress type for proper serialization
        const toAddress = AccountAddress.fromBase58(recipient)
        const amount = CcdAmount.fromMicroCcd(BigInt(amountMicroCCD))

        // The browser wallet API needs the properly typed payload
        const txHash = await provider.sendTransaction(
          account,
          AccountTransactionType.Transfer,
          {
            amount: amount,
            toAddress: toAddress
          }
        )

        console.log('Transaction response:', txHash)

        if (!txHash) {
          throw new Error('Transaction hash is empty')
        }

        console.log('Payment sent with hash:', txHash)
        return txHash
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Payment failed'
        console.error('Payment error details:', err)
        setError(message)
        throw err
      }
    },
    [account, provider]
  )

  useEffect(() => {
    // Listen for account changes
    if (provider && provider.on) {
      provider.on('accountChanged', (newAccount: string) => {
        setAccount(newAccount)
      })
    }
  }, [provider])

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
