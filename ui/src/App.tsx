import React, { useState } from 'react'
import DeviceDashboard from './DeviceDashboard'
import ContactsPage, { ContactLists } from './ContactsPage'
import CampaignWizard from './CampaignWizard'

export default function App() {
  const [page, setPage] = useState<'devices' | 'contacts' | 'campaign'>('devices')
  const [lists, setLists] = useState<ContactLists>({})

  return (
    <div>
      <nav style={{ marginBottom: 20 }}>
        <button onClick={() => setPage('devices')}>Devices</button>
        <button onClick={() => setPage('contacts')}>Contacts</button>
        <button onClick={() => setPage('campaign')}>Campaign</button>
      </nav>
      {page === 'devices' && <DeviceDashboard />}
      {page === 'contacts' && <ContactsPage lists={lists} setLists={setLists} />}
      {page === 'campaign' && <CampaignWizard lists={lists} />}
    </div>
  )
}
