'use client'

import { useState, useEffect, useRef } from 'react'
import { useWallet } from '@/lib/WalletContext'
import { WalletButton } from '@/components/WalletButton'

interface LogEntry {
  id: string
  timestamp: string
  type: 'prompt' | 'result' | 'payment' | 'error'
  content: string
  cost?: number
}

export default function Home() {
  const { isConnected, sendPayment } = useWallet()
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const logsEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    // Fetch available models
    const fetchModels = async () => {
      try {
        const response = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL}/models`
        )
        if (response.ok) {
          const data = await response.json()
          setModels(data.models || [])
          if (data.models && data.models.length > 0) {
            setSelectedModel(data.models[0])
          }
        }
      } catch (error) {
        console.error('Failed to fetch models:', error)
        addLog('error', `Failed to fetch models: ${error}`)
      }
    }

    fetchModels()
  }, [])

  useEffect(() => {
    // Auto-scroll to bottom of logs
    logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  const addLog = (type: LogEntry['type'], content: string, cost?: number) => {
    const newLog: LogEntry = {
      id: Date.now().toString(),
      timestamp: new Date().toLocaleTimeString(),
      type,
      content,
      cost,
    }
    setLogs((prev) => [...prev, newLog])
  }

  const runInference = async () => {
    if (!prompt.trim() || !selectedModel) {
      addLog('error', 'Please enter a prompt and select a model')
      return
    }

    if (!isConnected) {
      addLog('error', 'Please connect your wallet first')
      return
    }

    setLoading(true)
    addLog('prompt', `[${selectedModel}] ${prompt}`)

    try {
      // Step 1: Run inference
      const response = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL}/inference`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            model: selectedModel,
            prompt: prompt,
          }),
        }
      )

      if (response.ok) {
        const data = await response.json()
        const result = data.result || 'No result returned'
        addLog('result', result)

        // Step 2: Process payment if cost is returned
        const cost = data.cost || 0
        if (cost > 0) {
          addLog('payment', `Processing payment of ${cost} CCD...`)

          try {
            // Send automatic payment to the inference service
            const txHash = await sendPayment(
              process.env.NEXT_PUBLIC_INFERENCE_RECEIVER || 'C1KJPyQKKYsK8g3DAuHLq6ZFCL9ypzdCqAJxLJZVZ6j6kKGVmcT',
              cost
            )

            addLog('payment', `✓ Payment sent (${cost} CCD) - tx: ${txHash.substring(0, 16)}...`, cost)
          } catch (paymentErr) {
            addLog('error', `Payment failed: ${paymentErr instanceof Error ? paymentErr.message : 'Unknown error'}`)
          }
        } else {
          addLog('payment', '✓ Inference complete (no payment required)')
        }

        // Clear prompt after success
        setPrompt('')
      } else {
        addLog('error', 'Error running inference')
      }
    } catch (error) {
      addLog('error', `Error: ${error}`)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && e.ctrlKey) {
      runInference()
    }
  }

  return (
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
        {/* Sidebar - Models and Chat */}
        <div className="w-1/3 bg-white border-r border-gray-200 flex flex-col">
          {/* Model Selection */}
          <div className="p-4 border-b border-gray-200">
            <label className="block text-sm font-semibold text-gray-900 mb-2">
              Model
            </label>
            <select
              value={selectedModel}
              onChange={(e) => setSelectedModel(e.target.value)}
              className="w-full px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              {models.map((model) => (
                <option key={model} value={model}>
                  {model}
                </option>
              ))}
            </select>
          </div>

          {/* Chat Input */}
          <div className="flex-1 flex flex-col p-4">
            <label className="text-sm font-semibold text-gray-900 mb-2">
              Message (Ctrl+Enter to send)
            </label>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={4}
              className="flex-1 px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              placeholder="Enter your prompt here..."
            />
            <button
              onClick={runInference}
              disabled={loading || !isConnected}
              className="mt-3 w-full px-4 py-2 border border-gray-400 text-gray-900 font-semibold rounded-lg hover:border-gray-600 disabled:border-gray-300 disabled:text-gray-400 transition"
            >
              {loading ? 'Running...' : 'Send'}
            </button>
          </div>

          {/* Sidebar Info */}
          <div className="px-4 py-3 border-t border-gray-200 text-xs text-gray-600">
            <p>Status: {isConnected ? '✓ Connected' : '✗ Disconnected'}</p>
          </div>
        </div>

        {/* Logs Area */}
        <div className="flex-1 bg-white flex flex-col overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h2 className="text-lg font-semibold text-gray-900">Logs</h2>
          </div>

          <div className="flex-1 overflow-y-auto p-6 space-y-3">
            {logs.length === 0 ? (
              <div className="text-center py-12">
                <p className="text-gray-500 text-sm">No logs yet. Send a message to get started.</p>
              </div>
            ) : (
              logs.map((log) => (
                <div
                  key={log.id}
                  className={`p-3 rounded-lg font-mono text-sm bg-white border-l-4 ${
                    log.type === 'prompt'
                      ? 'border-l-blue-500 text-blue-700'
                      : log.type === 'result'
                        ? 'border-l-green-500 text-green-700'
                        : log.type === 'payment'
                          ? 'border-l-yellow-500 text-yellow-700'
                          : 'border-l-red-500 text-red-700'
                  } border border-gray-200`}
                >
                  <div className="flex items-start justify-between gap-2 mb-1">
                    <span className="text-gray-500 text-xs">{log.timestamp}</span>
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase text-gray-700 border border-gray-300">
                      {log.type}
                    </span>
                  </div>
                  <p className="whitespace-pre-wrap break-words">{log.content}</p>
                  {log.cost !== undefined && log.cost > 0 && (
                    <p className="text-xs text-gray-600 mt-1">Cost: {log.cost} CCD</p>
                  )}
                </div>
              ))
            )}
            <div ref={logsEndRef} />
          </div>
        </div>
      </div>
    </div>
  )
}
