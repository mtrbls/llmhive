'use client'

import { useState, useEffect, useRef } from 'react'
import { useWallet } from '@/lib/WalletContext'

interface LogEntry {
  id: string
  timestamp: string
  type: 'prompt' | 'inference' | 'error'
  content: string
  cost?: number
  tokenCount?: number
  needsPayment?: boolean
  txHash?: string
}

export default function Home() {
  const { isConnected, sendPayment } = useWallet()
  const [models, setModels] = useState<string[]>([])
  const [selectedModel, setSelectedModel] = useState('')
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [logs, setLogs] = useState<LogEntry[]>([])
  const [pendingPayment, setPendingPayment] = useState<{cost: number, logId: string} | null>(null)
  const [autoPayEnabled, setAutoPayEnabled] = useState(false)
  const logsEndRef = useRef<HTMLDivElement>(null)
  const logCounterRef = useRef(0)

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
      id: `${Date.now()}-${logCounterRef.current++}`,
      timestamp: new Date().toLocaleTimeString(),
      type,
      content,
      cost,
    }
    setLogs((prev) => [...prev, newLog])
  }

  const handleManualPayment = async () => {
    if (!pendingPayment) return

    try {
      const receiverAddress = process.env.NEXT_PUBLIC_INFERENCE_RECEIVER
      if (!receiverAddress) {
        addLog('error', 'Inference service address not configured. Set NEXT_PUBLIC_INFERENCE_RECEIVER in .env.local')
        return
      }

      const txHash = await sendPayment(receiverAddress, pendingPayment.cost)

      // Update the existing log entry with the transaction hash
      setLogs((prev) =>
        prev.map((log) =>
          log.id === pendingPayment.logId
            ? { ...log, needsPayment: false, txHash: txHash || undefined }
            : log
        )
      )

      setPendingPayment(null) // Clear pending payment
    } catch (paymentErr) {
      addLog('error', `Payment failed: ${paymentErr instanceof Error ? paymentErr.message : 'Unknown error'}`)
    }
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
        // Handle streaming NDJSON response
        const text = await response.text()
        const lines = text.trim().split('\n').filter(line => line.length > 0)

        let result = ''
        let cost = 0
        let totalTokens = 0
        const PRICE_PER_TOKEN = 0.0001 // CCD per token

        // Parse each line as JSON
        for (const line of lines) {
          try {
            const data = JSON.parse(line)
            if (data.error) {
              addLog('error', data.error)
            } else if (data.token_counts) {
              // Calculate cost based on total tokens
              if (data.token_counts.total_tokens) {
                totalTokens = data.token_counts.total_tokens
                cost = totalTokens * PRICE_PER_TOKEN
              }
            } else if (data.token) {
              // Accumulate output tokens into result
              result += data.token
            }
          } catch (parseErr) {
            // Skip lines that aren't valid JSON
          }
        }

        if (result) {
          // Create a bundled log entry with response, tokens, and payment info
          const inferenceLog: LogEntry = {
            id: `${Date.now()}-${logCounterRef.current++}`,
            timestamp: new Date().toLocaleTimeString(),
            type: 'inference',
            content: result,
            cost: cost > 0 ? cost : undefined,
            tokenCount: totalTokens > 0 ? totalTokens : undefined,
            needsPayment: cost > 0 && !autoPayEnabled, // Only needs manual payment if autopay is off
          }
          setLogs((prev) => [...prev, inferenceLog])

          if (cost > 0) {
            if (autoPayEnabled) {
              // Automatically initiate payment (wallet will still require manual approval for security)
              // This is a security feature of browser wallets that cannot be bypassed
              try {
                const receiverAddress = process.env.NEXT_PUBLIC_INFERENCE_RECEIVER
                if (!receiverAddress) {
                  addLog('error', 'Inference service address not configured. Set NEXT_PUBLIC_INFERENCE_RECEIVER in .env.local')
                  return
                }

                const txHash = await sendPayment(receiverAddress, cost)

                // Update the inference log with the transaction hash
                setLogs((prev) =>
                  prev.map((log) =>
                    log.id === inferenceLog.id
                      ? { ...log, needsPayment: false, txHash: txHash || undefined }
                      : log
                  )
                )
              } catch (paymentErr) {
                addLog('error', `Auto-payment failed: ${paymentErr instanceof Error ? paymentErr.message : 'Unknown error'}`)
                // Fall back to manual payment on error
                setPendingPayment({ cost, logId: inferenceLog.id })
              }
            } else {
              // Manual payment required
              setPendingPayment({ cost, logId: inferenceLog.id })
            }
          }
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
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Logs Section - Now at the top */}
      <div className="flex-1 flex flex-col overflow-hidden border-b border-gray-200">
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
                    : log.type === 'inference'
                      ? 'border-l-green-500 text-green-700'
                      : 'border-l-red-500 text-red-700'
                } border border-gray-200`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="text-gray-500 text-xs">{log.timestamp}</span>
                  <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold uppercase text-gray-700 border border-gray-300">
                    {log.type === 'inference' ? 'RESPONSE' : log.type}
                  </span>
                </div>
                <p className="whitespace-pre-wrap break-words">{log.content}</p>

                {/* For inference logs, show tokens and cost info in a unified way */}
                {log.type === 'inference' && (
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    {log.tokenCount && (
                      <p className="text-xs text-gray-600">Tokens: {log.tokenCount}</p>
                    )}
                    {log.cost && (
                      <p className="text-xs text-gray-600">Cost: {log.cost} CCD</p>
                    )}
                    {/* Show Pay Now button if payment needed */}
                    {log.needsPayment && pendingPayment?.logId === log.id && (
                      <button
                        onClick={handleManualPayment}
                        className="mt-2 px-4 py-1.5 bg-blue-600 text-white font-semibold text-xs rounded hover:bg-blue-700 transition"
                      >
                        Pay Now ({log.cost} CCD)
                      </button>
                    )}
                    {/* Show transaction hash if payment completed */}
                    {log.txHash && (
                      <div className="flex items-center gap-2 mt-1">
                        <span className="text-xs text-green-600 font-semibold">✓ Paid</span>
                        <a
                          href={`https://testnet.ccdscan.io/?dcount=1&dentity=transaction&dhash=${log.txHash}`}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="text-xs text-blue-600 hover:text-blue-800 underline"
                        >
                          tx: {log.txHash.length > 16 ? log.txHash.substring(0, 16) + '...' : log.txHash}
                        </a>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))
          )}
          <div ref={logsEndRef} />
        </div>
      </div>

      {/* Chat Input Section - Now at the bottom */}
      <div className="flex flex-col">
        {/* Model Selection and Settings */}
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <label className="block text-sm font-semibold text-gray-900 mb-2">
                Model
              </label>
              <div className="flex gap-2">
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-1/3 px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {models.map((model) => (
                    <option key={model} value={model}>
                      {model}
                    </option>
                  ))}
                </select>
                <button
                  onClick={async () => {
                    const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/models`)
                    if (response.ok) {
                      const data = await response.json()
                      setModels(data.models || [])
                    }
                  }}
                  className="px-3 py-2 border border-gray-400 text-gray-900 font-semibold rounded-lg hover:border-gray-600 transition"
                >
                  ↻
                </button>
              </div>
            </div>

            {/* Autopayment Toggle */}
            <div className="ml-6">
              <label className="flex items-center cursor-pointer">
                <input
                  type="checkbox"
                  checked={autoPayEnabled}
                  onChange={(e) => setAutoPayEnabled(e.target.checked)}
                  className="sr-only peer"
                />
                <div className="relative w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-blue-600"></div>
                <span className="ml-3 text-sm font-semibold text-gray-900">Auto-initiate</span>
              </label>
              <p className="mt-1 text-xs text-gray-500">
                {autoPayEnabled ? 'Auto-initiates payment (wallet approval required)' : 'Manual payment button required'}
              </p>
            </div>
          </div>
        </div>

        {/* Chat Input */}
        <div className="p-4">
          <label className="text-sm font-semibold text-gray-900 mb-2 block">
            Message (Ctrl+Enter to send)
          </label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={3}
            className="w-full px-3 py-2 bg-white border border-gray-300 text-gray-900 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
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
      </div>
    </div>
  )
}
