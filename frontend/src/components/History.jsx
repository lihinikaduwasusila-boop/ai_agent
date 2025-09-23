import React, { useEffect, useState } from 'react'
import { api } from '../api'

export default function History() {
  const [items, setItems] = useState([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    (async () => {
      setLoading(true)
      setError('')
      try {
        const res = await api('/history', 'GET')
        setItems(res.items || [])
      } catch (err) {
        setError(err.message)
      } finally {
        setLoading(false)
      }
    })()
  }, [])

  if (loading) return <div>Loading…</div>
  if (error) return <div style={{ color: 'red' }}>{error}</div>

  return (
    <div>
      <h3>Previous Searches</h3>
      {!items.length && <div>No history yet.</div>}
      {items.map(i => (
        <details key={i.id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, marginBottom: 8 }}>
          <summary>
            <strong>{i.query}</strong>
            <span style={{ marginLeft: 8, color: '#6b7280' }}>{i.timestamp}</span>
          </summary>
          <pre style={{ whiteSpace: 'pre-wrap' }}>{JSON.stringify(i.results, null, 2)}</pre>
        </details>
      ))}
    </div>
  )
}