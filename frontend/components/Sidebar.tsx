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
    <div className="w-64 bg-gray-50 border-r border-gray-200 flex flex-col">
      {/* Sidebar Header */}
      <div className="p-6 border-b border-gray-200">
        <h2 className="text-sm font-bold uppercase tracking-wider text-gray-700">Menu</h2>
      </div>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2">
        <Link
          href="/"
          className={`block px-4 py-3 rounded-lg font-semibold text-gray-900 transition ${
            isActive('/') ? 'bg-gray-200 hover:bg-gray-300' : 'hover:bg-gray-100'
          }`}
        >
          Inference
        </Link>
        <Link
          href="/nodes"
          className={`block px-4 py-3 rounded-lg font-semibold text-gray-900 transition ${
            isActive('/nodes') ? 'bg-gray-200 hover:bg-gray-300' : 'hover:bg-gray-100'
          }`}
        >
          Nodes
        </Link>
        <Link
          href="/settings"
          className={`block px-4 py-3 rounded-lg font-semibold text-gray-900 transition ${
            isActive('/settings') ? 'bg-gray-200 hover:bg-gray-300' : 'hover:bg-gray-100'
          }`}
        >
          Settings
        </Link>
      </nav>

      {/* Sidebar Footer */}
      <div className="p-4 border-t border-gray-200 space-y-3">
        <div className="px-4 py-3 bg-white rounded-lg border border-gray-200">
          <p className="text-xs font-semibold text-gray-700 mb-1">WALLET STATUS</p>
          <p className="text-sm font-semibold text-gray-900">
            {isConnected ? '✓ Connected' : '✗ Disconnected'}
          </p>
        </div>
      </div>
    </div>
  )
}
