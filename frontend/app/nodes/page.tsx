'use client'

import { useState, useEffect } from 'react'

interface Node {
  node_id: string
  url: string
  models: string[]
  last_seen: string
}

interface NodeDisplay {
  id: string
  address: string
  status: string
  model?: string
}

export default function NodesPage() {
  const [nodes, setNodes] = useState<NodeDisplay[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchNodes()
  }, [])

  const fetchNodes = async () => {
    setLoading(true)
    setError(null)
    try {
      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://35.158.225.20:8000'
      const response = await fetch(`${apiUrl}/nodes`)
      if (response.ok) {
        const data = await response.json()
        // Transform API response to match UI expectations
        const displayNodes = (data.nodes || []).map((node: Node) => {
          const lastSeen = new Date(node.last_seen)
          const now = new Date()
          const isOnline = (now.getTime() - lastSeen.getTime()) < 60000 // Online if seen within 60 seconds

          return {
            id: node.node_id,
            address: node.url,
            status: isOnline ? 'online' : 'offline',
            model: node.models && node.models.length > 0 ? node.models[0] : undefined
          }
        })
        setNodes(displayNodes)
      } else {
        setError('Failed to fetch nodes')
      }
    } catch (err) {
      setError(`Error: ${err}`)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="p-6 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <h2 className="text-2xl font-bold text-gray-900">Registered Nodes</h2>
          <button
            onClick={fetchNodes}
            className="px-4 py-2 border border-gray-400 text-gray-900 font-semibold rounded-lg hover:border-gray-600 transition"
          >
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-600">Loading nodes...</p>
          </div>
        ) : error ? (
          <div className="p-4 rounded-lg border border-red-300 bg-white text-red-700">
            {error}
          </div>
        ) : nodes.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-gray-600">No nodes registered yet</p>
          </div>
        ) : (
          <div className="space-y-3">
            {nodes.map((node) => (
              <div
                key={node.id}
                className="p-4 rounded-lg border border-gray-200 bg-white hover:border-gray-400 transition"
              >
                <div className="flex items-start justify-between mb-2">
                  <div>
                    <h3 className="font-semibold text-gray-900">{node.id}</h3>
                    <p className="text-sm text-gray-600 font-mono">{node.address}</p>
                  </div>
                  <span
                    className={`px-3 py-1 rounded-full text-xs font-semibold ${
                      node.status === 'online'
                        ? 'bg-white border border-green-500 text-green-700'
                        : 'bg-white border border-red-500 text-red-700'
                    }`}
                  >
                    {node.status}
                  </span>
                </div>
                {node.model && (
                  <p className="text-sm text-gray-700">
                    <span className="font-semibold">Model:</span> {node.model}
                  </p>
                )}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
