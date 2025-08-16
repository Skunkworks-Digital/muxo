import React, { useState, useEffect } from 'react'
import { ContactLists, Contact } from './ContactsPage'

interface Props {
  lists: ContactLists
}

const renderTemplate = (template: string, c: Contact) =>
  template.replace(/{{(.*?)}}/g, (_, k) => {
    const key = k.trim() as keyof Contact
    return (c[key] as string) ?? ''
  })

export default function CampaignWizard({ lists }: Props) {
  const [step, setStep] = useState(0)
  const [listName, setListName] = useState('')
  const [template, setTemplate] = useState('Hello {{first_name}}')
  const [schedule, setSchedule] = useState({ start: '', end: '' })
  const [rate, setRate] = useState(1)
  const [progress, setProgress] = useState(0)
  const [running, setRunning] = useState(false)

  const selected = lists[listName] || []
  const total = selected.length

  const next = () => setStep(s => Math.min(s + 1, 3))
  const prev = () => setStep(s => Math.max(s - 1, 0))

  const startCampaign = () => {
    setRunning(true)
    setProgress(0)
  }

  useEffect(() => {
    if (running && progress < total) {
      const id = setTimeout(() => setProgress(p => p + 1), 1000 / rate)
      return () => clearTimeout(id)
    }
    if (progress >= total && running) setRunning(false)
  }, [running, progress, total, rate])

  return (
    <div>
      {step === 0 && (
        <div>
          <h3>Select list</h3>
          <select value={listName} onChange={e => setListName(e.target.value)}>
            <option value="">-- Choose --</option>
            {Object.keys(lists).map(l => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>
      )}
      {step === 1 && (
        <div>
          <h3>Template</h3>
          <textarea
            value={template}
            onChange={e => setTemplate(e.target.value)}
            rows={4}
            cols={40}
          />
          <div>
            <strong>Preview:</strong>
            <ul>
              {selected.slice(0, 3).map(c => (
                <li key={c.msisdn}>{renderTemplate(template, c)}</li>
              ))}
            </ul>
          </div>
        </div>
      )}
      {step === 2 && (
        <div>
          <h3>Schedule window</h3>
          <input
            type="datetime-local"
            value={schedule.start}
            onChange={e => setSchedule({ ...schedule, start: e.target.value })}
          />
          <input
            type="datetime-local"
            value={schedule.end}
            onChange={e => setSchedule({ ...schedule, end: e.target.value })}
          />
        </div>
      )}
      {step === 3 && (
        <div>
          <h3>Rate</h3>
          <input
            type="number"
            value={rate}
            onChange={e => setRate(Number(e.target.value) || 1)}
          />{' '}
          msg/s
          <div style={{ marginTop: 10 }}>
            <button onClick={startCampaign} disabled={!listName || running}>
              Start Campaign
            </button>
            {running && (
              <div>
                Sent {progress} / {total}
              </div>
            )}
          </div>
        </div>
      )}
      <div style={{ marginTop: 20 }}>
        {step > 0 && <button onClick={prev}>Back</button>}
        {step < 3 && <button onClick={next} disabled={step === 0 && !listName}>Next</button>}
      </div>
    </div>
  )
}
