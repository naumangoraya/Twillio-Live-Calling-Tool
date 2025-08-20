import React, { useEffect, useMemo, useRef, useState } from 'react'

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL || 'http://127.0.0.1:5000'

type StatusEvent = {
  event: string
  payload: any
}

type TwilioStatus = {
  connected: boolean
  message: string
  current_auth_method: string
  primary_client_available: boolean
  fallback_client_available: boolean
  account_sid_configured: boolean
  api_key_configured: boolean
  auth_token_configured: boolean
}

export default function App() {
  const [customerNumber, setCustomerNumber] = useState('')
  const [agentNumber, setAgentNumber] = useState('')
  const [logs, setLogs] = useState<string[]>([])
  const [connecting, setConnecting] = useState(false)
  const [connected, setConnected] = useState(false)
  const [twilioStatus, setTwilioStatus] = useState<TwilioStatus | null>(null)
  const [loadingStatus, setLoadingStatus] = useState(true)
  const eventSourceRef = useRef<EventSource | null>(null)

  const appendLog = (line: string) => setLogs((prev) => [new Date().toLocaleTimeString() + ' ' + line, ...prev])

  const eventsUrl = useMemo(() => `${BACKEND_URL}/api/events`, [])

  // Check Twilio status on component mount
  useEffect(() => {
    checkTwilioStatus()
  }, [])

  const checkTwilioStatus = async () => {
    try {
      const response = await fetch(`${BACKEND_URL}/api/twilio/status`)
      const status = await response.json()
      setTwilioStatus(status)
      appendLog(`Twilio status: ${status.message}`)
    } catch (error) {
      appendLog(`Failed to check Twilio status: ${error}`)
    } finally {
      setLoadingStatus(false)
    }
  }

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
          const authMethod = p.auth_method ? ` using ${p.auth_method}` : ''
          appendLog(`Dialing agent ${p.to}, then customer ${p.customer}. SID: ${p.sid}${authMethod}`)
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
      
      const authMethod = data.auth_method ? ` using ${data.auth_method} authentication` : ''
      appendLog(`Call created SID: ${data.sid}${authMethod}`)
    } catch (e: any) {
      appendLog(`Error: ${e.message}`)
    } finally {
      setConnecting(false)
    }
  }

  const getStatusColor = (connected: boolean) => {
    return connected ? 'text-green-600' : 'text-red-600'
  }

  const getAuthMethodDisplay = (method: string) => {
    switch (method) {
      case 'auth_token':
        return 'Auth Token (Primary)'
      case 'api_key':
        return 'API Key (Fallback)'
      case 'none':
        return 'None'
      default:
        return method
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <div className="mx-auto max-w-4xl p-6">
        <header className="mb-6">
          <h1 className="text-2xl font-bold">Twilio Live Call Bridge</h1>
          <p className="text-sm text-slate-600">Dial agent first, then bridge to customer for real-time voice.</p>
        </header>

        {/* Twilio Status Section */}
        <div className="mb-6 rounded-lg border border-slate-200 bg-white p-4">
          <h2 className="mb-3 text-lg font-semibold">Twilio Connection Status</h2>
          {loadingStatus ? (
            <div className="text-slate-500">Checking Twilio status...</div>
          ) : twilioStatus ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Status:</span>
                <span className={`font-semibold ${getStatusColor(twilioStatus.connected)}`}>
                  {twilioStatus.connected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium">Method:</span>
                <span className="font-mono text-sm">
                  {getAuthMethodDisplay(twilioStatus.current_auth_method)}
                </span>
              </div>
              <div className="text-sm text-slate-600">{twilioStatus.message}</div>
              
              {/* Configuration Status */}
              <div className="mt-3 grid grid-cols-2 gap-4 text-xs">
                <div className="space-y-1">
                  <div className={`${twilioStatus.account_sid_configured ? 'text-green-600' : 'text-red-600'}`}>
                    ✓ Account SID: {twilioStatus.account_sid_configured ? 'Configured' : 'Missing'}
                  </div>
                  <div className={`${twilioStatus.api_key_configured ? 'text-green-600' : 'text-red-600'}`}>
                    ✓ API Key: {twilioStatus.api_key_configured ? 'Configured' : 'Missing'}
                  </div>
                  <div className={`${twilioStatus.auth_token_configured ? 'text-green-600' : 'text-red-600'}`}>
                    ✓ Auth Token: {twilioStatus.auth_token_configured ? 'Configured' : 'Missing'}
                  </div>
                </div>
                <div className="space-y-1">
                  <div className={`${twilioStatus.primary_client_available ? 'text-green-600' : 'text-red-600'}`}>
                    ✓ Primary Client: {twilioStatus.primary_client_available ? 'Available' : 'Unavailable'}
                  </div>
                  <div className={`${twilioStatus.fallback_client_available ? 'text-green-600' : 'text-red-600'}`}>
                    ✓ Fallback Client: {twilioStatus.fallback_client_available ? 'Available' : 'Unavailable'}
                  </div>
                </div>
              </div>
              
              {!twilioStatus.connected && (
                <div className="mt-3 rounded-md bg-yellow-50 p-3 text-sm text-yellow-800">
                  <strong>Connection Issue:</strong> Please check your Twilio credentials in the environment variables.
                  The application will automatically try to use fallback authentication if the primary method fails.
                </div>
              )}
            </div>
          ) : (
            <div className="text-red-600">Failed to load Twilio status</div>
          )}
        </div>

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
            disabled={connecting || !twilioStatus?.connected}
            className="rounded-md bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {connecting ? 'Dialing…' : 'Call'}
          </button>
          {connected && <span className="text-green-600 text-sm">Call in progress</span>}
          {!twilioStatus?.connected && (
            <span className="text-red-600 text-sm">Twilio not connected</span>
          )}
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


