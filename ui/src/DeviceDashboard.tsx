import React, { useState } from 'react'

interface Device {
  id: number
  status: string
  signal: number
  operator: string
  lastSeen: string
  transcript: string[]
}

const probeDevices = (): Device[] => [
  {
    id: 1,
    status: 'online',
    signal: 80,
    operator: 'MuxTel',
    lastSeen: new Date().toLocaleString(),
    transcript: ['AT+CSQ', '+CSQ: 20,99']
  },
  {
    id: 2,
    status: 'offline',
    signal: 0,
    operator: '-',
    lastSeen: new Date().toLocaleString(),
    transcript: []
  }
]

export default function DeviceDashboard() {
  const [devices, setDevices] = useState<Device[]>([])
  const [selected, setSelected] = useState<Device | null>(null)
  const [sms, setSms] = useState('')

  const handleProbe = () => setDevices(probeDevices())

  const sendSms = (e: React.FormEvent) => {
    e.preventDefault()
    if (!selected || !sms.trim()) return
    const updated = { ...selected, transcript: [...selected.transcript, `> ${sms}`] }
    setSelected(updated)
    setDevices(devices.map(d => (d.id === updated.id ? updated : d)))
    setSms('')
  }

  return (
    <div>
      <button onClick={handleProbe}>Probe</button>
      <table border={1} cellPadding={4} style={{ marginTop: 10 }}>
        <thead>
          <tr>
            <th>ID</th>
            <th>Status</th>
            <th>Signal</th>
            <th>Operator</th>
            <th>Last Seen</th>
          </tr>
        </thead>
        <tbody>
          {devices.map(d => (
            <tr key={d.id} onClick={() => setSelected(d)} style={{ cursor: 'pointer' }}>
              <td>{d.id}</td>
              <td>{d.status}</td>
              <td>{d.signal}</td>
              <td>{d.operator}</td>
              <td>{d.lastSeen}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {selected && (
        <div style={{ border: '1px solid #ccc', padding: 10, marginTop: 20 }}>
          <h3>Device {selected.id}</h3>
          <div>
            <strong>Transcript tail:</strong>
            <ul>
              {selected.transcript.slice(-5).map((t, i) => (
                <li key={i}>{t}</li>
              ))}
            </ul>
          </div>
          <form onSubmit={sendSms}>
            <input
              value={sms}
              onChange={e => setSms(e.target.value)}
              placeholder="Send test SMS"
            />
            <button type="submit">Send</button>
          </form>
        </div>
      )}
    </div>
  )
}
