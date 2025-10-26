'use client'

import { useState } from 'react'
import { useWallet } from '@/lib/WalletContext'

export default function SettingsPage() {
  const { account } = useWallet()
  const [apiUrl, setApiUrl] = useState(process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000')
  const [saved, setSaved] = useState(false)

  const handleSave = () => {
    localStorage.setItem('api_url', apiUrl)
    setSaved(true)
    setTimeout(() => setSaved(false), 3000)
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-2xl font-bold text-gray-900">Settings</h2>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl space-y-6">
          {/* API Settings */}
          <div className="p-6 rounded-lg border border-gray-200 bg-white">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">API Configuration</h3>
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-gray-900 mb-2">
                  API URL
                </label>
                <input
                  type="text"
                  value={apiUrl}
                  onChange={(e) => setApiUrl(e.target.value)}
                  className="w-full px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="http://localhost:8000"
                />
                <p className="text-xs text-gray-600 mt-2">
                  The URL of the inference server API
                </p>
              </div>
              <button
                onClick={handleSave}
                className="px-4 py-2 border border-gray-400 text-gray-900 font-semibold rounded-lg hover:border-gray-600 transition"
              >
                Save Settings
              </button>
              {saved && (
                <p className="text-sm text-green-700 border border-green-300 p-2 rounded">
                  Settings saved successfully
                </p>
              )}
            </div>
          </div>

          {/* Wallet Info */}
          <div className="p-6 rounded-lg border border-gray-200 bg-white">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Wallet Information</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1">Account Address</p>
                <p className="text-sm font-mono text-gray-900 break-all">
                  {account ? account : 'No wallet connected'}
                </p>
              </div>
            </div>
          </div>

          {/* Application Info */}
          <div className="p-6 rounded-lg border border-gray-200 bg-white">
            <h3 className="text-lg font-semibold text-gray-900 mb-4">Application</h3>
            <div className="space-y-3">
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1">Version</p>
                <p className="text-sm text-gray-900">1.0.0</p>
              </div>
              <div>
                <p className="text-xs font-semibold text-gray-700 mb-1">Network</p>
                <p className="text-sm text-gray-900">Concordium Testnet</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
