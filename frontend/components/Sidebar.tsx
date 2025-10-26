'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { useWallet } from '@/lib/WalletContext'

export function Sidebar() {
  const pathname = usePathname()
  const { isConnected } = useWallet()

  const isActive = (path: string) => {
    return pathname === path || (path === '/' && pathname === '/')
  }

  return (
    <div className="w-64 bg-gray-50 border-r-2 border-black flex flex-col">
      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2 pt-6">
        <Link
          href="/"
          className={`block px-4 py-3 rounded-lg font-semibold text-gray-900 transition ${
            isActive('/') ? 'border-2 border-black' : 'hover:bg-gray-100'
          }`}
        >
          Inference
        </Link>
        <Link
          href="/nodes"
          className={`block px-4 py-3 rounded-lg font-semibold text-gray-900 transition ${
            isActive('/nodes') ? 'border-2 border-black' : 'hover:bg-gray-100'
          }`}
        >
          Nodes
        </Link>
        <Link
          href="/settings"
          className={`block px-4 py-3 rounded-lg font-semibold text-gray-900 transition ${
            isActive('/settings') ? 'border-2 border-black' : 'hover:bg-gray-100'
          }`}
        >
          Settings
        </Link>
      </nav>

      {/* Sidebar Footer */}
      <div className="p-4 border-t-2 border-black space-y-3">
        <div className="px-4 py-3 bg-white rounded-lg border-2 border-black">
          <p className="text-xs font-semibold text-gray-700 mb-1">WALLET STATUS</p>
          <p className="text-sm font-semibold text-gray-900">
            {isConnected ? '✓ Connected' : '✗ Disconnected'}
          </p>
        </div>
      </div>
    </div>
  )
}
