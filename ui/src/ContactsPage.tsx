import React, { useState } from 'react'

export interface Contact {
  msisdn: string
  first_name: string
  last_name: string
  tags: string[]
  optedOut: boolean
}

export interface ContactLists {
  [name: string]: Contact[]
}

interface Props {
  lists: ContactLists
  setLists: (lists: ContactLists) => void
}

interface Row extends Contact {
  include: boolean
}

const parseCsv = (text: string): Row[] => {
  const lines = text.trim().split(/\r?\n/)
  return lines.map(l => {
    const [msisdn, first_name, last_name, tagStr = ''] = l.split(',')
    const tags = tagStr.split(';').map(t => t.trim()).filter(Boolean)
    const optedOut = tags.some(t => t.toLowerCase().includes('opt'))
    return { msisdn, first_name, last_name, tags, optedOut, include: true }
  })
}

export default function ContactsPage({ lists, setLists }: Props) {
  const [rows, setRows] = useState<Row[]>([])
  const [listName, setListName] = useState('')

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const text = await file.text()
    setRows(parseCsv(text))
  }

  const toggleInclude = (i: number) =>
    setRows(rows.map((r, idx) => (idx === i ? { ...r, include: !r.include } : r)))

  const createList = () => {
    if (!listName.trim()) return
    const contacts = rows
      .filter(r => r.include && !r.optedOut)
      .map(
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        ({ include: _include, ...c }) => c,
      )
    setLists({ ...lists, [listName]: contacts })
    setListName('')
  }

  const toggleMembership = (list: string, c: Contact) => {
    const current = lists[list] || []
    const exists = current.some(x => x.msisdn === c.msisdn)
    const updated = exists
      ? current.filter(x => x.msisdn !== c.msisdn)
      : [...current, c]
    setLists({ ...lists, [list]: updated })
  }

  return (
    <div>
      <input type="file" accept=".csv" onChange={handleFile} />
      {rows.length > 0 && (
        <div>
          <table border={1} cellPadding={4} style={{ marginTop: 10 }}>
            <thead>
              <tr>
                <th>Include</th>
                <th>MSISDN</th>
                <th>First</th>
                <th>Last</th>
                <th>Tags</th>
                {Object.keys(lists).map(l => (
                  <th key={l}>{l}</th>
                ))}
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r, i) => (
                <tr key={i}>
                  <td>
                    <input
                      type="checkbox"
                      checked={r.include}
                      onChange={() => toggleInclude(i)}
                      disabled={r.optedOut}
                    />
                  </td>
                  <td>{r.msisdn}</td>
                  <td>{r.first_name}</td>
                  <td>{r.last_name}</td>
                  <td>{r.tags.join(';')}</td>
                  {Object.keys(lists).map(l => (
                    <td key={l}>
                      <input
                        type="checkbox"
                        checked={
                          lists[l].some(c => c.msisdn === r.msisdn)
                        }
                        onChange={() => toggleMembership(l, r)}
                        disabled={r.optedOut}
                      />
                    </td>
                  ))}
                  <td>{r.optedOut && <span style={{ color: 'red' }}>Opt-out</span>}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div style={{ marginTop: 10 }}>
            <input
              value={listName}
              onChange={e => setListName(e.target.value)}
              placeholder="New list name"
            />
            <button onClick={createList}>Create List</button>
          </div>
        </div>
      )}
      {Object.keys(lists).length > 0 && (
        <div style={{ marginTop: 20 }}>
          <h3>Lists</h3>
          {Object.entries(lists).map(([name, list]) => (
            <div key={name} style={{ marginBottom: 10 }}>
              <strong>{name}</strong> ({list.length} contacts)
              <ul>
                {list.map(c => (
                  <li key={c.msisdn}>
                    {c.msisdn} {c.first_name} {c.last_name}
                    <button
                      onClick={() =>
                        toggleMembership(
                          name,
                          c
                        )
                      }
                    >
                      Remove
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
