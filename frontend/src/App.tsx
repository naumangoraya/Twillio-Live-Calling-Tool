import React, { useEffect, useMemo, useRef, useState } from 'react'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:5000'

type StatusEvent = {
  event: string
  payload: any
}

export default function App() {
  const [customerNumber, setCustomerNumber] = useState('')
  const [agentNumber, setAgentNumber] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [connecting, setConnecting] = useState(false)
  const [connected, setConnected] = useState(false)
  const eventSourceRef = useRef<EventSource | null>(null)

  const appendLog = (line: string) => setLogs((prev) => [new Date().toLocaleTimeString() + ' ' + line, ...prev])

  const eventsUrl = useMemo(() => `${BACKEND_URL}/api/events`, [])

  useEffect(() => {
    const es = new EventSource(eventsUrl)
    eventSourceRef.current = es
    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as StatusEvent
        if (data.event === 'connected') {
          appendLog('Connected to events.')
        } else if (data.event === 'incoming_call') {
          const p = data.payload
          appendLog(`Incoming call on ${p.which}: from ${p.from} to ${p.to}`)
        } else if (data.event === 'call_status') {
          const p = data.payload
          appendLog(`Call ${p.CallSid} status: ${p.CallStatus}`)
          setConnected(p.CallStatus === 'in-progress' || p.CallStatus === 'answered')
        } else if (data.event === 'call_initiated') {
          const p = data.payload
          appendLog(`Dialing agent ${p.to}, then customer ${p.customer}. SID: ${p.sid}`)
        }
      } catch (e) {
        // ignore
      }
    }
    es.onerror = () => {
      appendLog('Events connection error. Refresh page to reconnect.')
    }
    return () => {
      es.close()
    }
  }, [eventsUrl])

  const startCall = async () => {
    if (!customerNumber) {
      alert('Enter customer number in E.164 format, e.g., +12345550100')
      return
    }
    setConnecting(true)
    try {
      const res = await fetch(`${BACKEND_URL}/api/call/connect`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ customer_number: customerNumber, agent_number: agentNumber || undefined }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to start call')
      appendLog(`Call created SID: ${data.sid}`)
    } catch (e: any) {
      appendLog(`Error: ${e.message}`)
    } finally {
      setConnecting(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-3xl p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-bold">Twilio Live Call Bridge</h1>
          <p className="text-sm text-slate-600">Dial agent first, then bridge to customer for real-time voice.</p>
        </header>

        <div className="grid gap-4 sm:grid-cols-2">
          <div className="space-y-2">
            <label className="block text-sm font-medium">Customer number</label>
            <input
              value={customerNumber}
              onChange={(e) => setCustomerNumber(e.target.value)}
              placeholder="+12345550100"
              className="w-full rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="text-xs text-slate-500">The callee your agent will connect to after answering.</p>
          </div>
          <div className="space-y-2">
            <label className="block text-sm font-medium">Agent number (optional)</label>
            <input
              value={agentNumber}
              onChange={(e) => setAgentNumber(e.target.value)}
              placeholder="Defaults to TWILIO_NUMBER_B"
              className="w-full rounded-md border border-slate-300 px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <p className="text-xs text-slate-500">Leave empty to use your configured Twilio Number B.</p>
          </div>
        </div>

        <div className="mt-4 flex items-center gap-3">
          <button
            onClick={startCall}
            disabled={connecting}
            className="rounded-md bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {connecting ? 'Dialing…' : 'Call'}
          </button>
          {connected && <span className="text-green-600 text-sm">Call in progress</span>}
        </div>

        <div className="mt-8">
          <h2 className="mb-2 text-lg font-semibold">Activity</h2>
          <div className="h-64 overflow-auto rounded-md border border-slate-200 bg-white p-3 text-sm">
            {logs.length === 0 ? (
              <div className="text-slate-500">No events yet.</div>
            ) : (
              <ul className="space-y-1">
                {logs.map((l, idx) => (
                  <li key={idx} className="font-mono">
                    {l}
                  </li>
                ))}
              </ul>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}


