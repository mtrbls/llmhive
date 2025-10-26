'use client'

import { useWallet } from '@/lib/WalletContext'
import { useState } from 'react'

export function WalletButton() {
  const { account, isConnected, isConnecting, connectWallet, disconnectWallet, error } = useWallet()
  const [showError, setShowError] = useState(false)

  const handleConnect = async () => {
    try {
      setShowError(false)
      await connectWallet()
    } catch (err) {
      setShowError(true)
    }
  }

  const handleDisconnect = () => {
    disconnectWallet()
    setShowError(false)
  }

  return (
    <div className="space-y-2">
      <button
        onClick={isConnected ? handleDisconnect : handleConnect}
        disabled={isConnecting}
        className={`px-6 py-2 rounded-lg font-medium transition border ${
          isConnected
            ? 'border-gray-400 text-gray-900 hover:border-gray-600'
            : 'border-gray-400 text-gray-900 hover:border-gray-600 disabled:border-gray-300 disabled:text-gray-400'
        }`}
      >
        {isConnecting
          ? 'Connecting...'
          : isConnected
            ? `✓ Wallet Connected (${account?.substring(0, 10)}...)`
            : 'Connect Wallet'}
      </button>
      {error && showError && (
        <p className="text-sm text-red-700 border border-red-300 p-2 rounded">{error}</p>
      )}
    </div>
  )
}
