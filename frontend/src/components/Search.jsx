import React, { useState } from 'react'
import { api } from '../api'

export default function Search() {
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const onSearch = async (e) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    setResult(null)
    try {
      const res = await api('/query', 'POST', { query })
      setResult(res)
    } catch (err) {
      setError(err.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <form onSubmit={onSearch} style={{ display: 'grid', gridTemplateColumns: '1fr auto', gap: 8 }}>
        <input placeholder="e.g. scotus cyber fraud 2020 to 2025" value={query} onChange={e => setQuery(e.target.value)} />
        <button disabled={loading}>{loading ? 'Searching…' : 'Search'}</button>
      </form>
      {error && <div style={{ color: 'red', marginTop: 8 }}>{error}</div>}

      {result && (
        <div style={{ marginTop: 16 }}>
          <h3>Results</h3>
          {result.cases?.length ? result.cases.map(c => (
            <div key={c.case_id} style={{ border: '1px solid #e5e7eb', borderRadius: 8, padding: 12, marginBottom: 8 }}>
              <div style={{ fontWeight: 600 }}>{c.case_name}</div>
              <div style={{ fontSize: 14, color: '#374151' }}>Court: {c.court}</div>
              <div style={{ fontSize: 14, color: '#374151' }}>Decision: {c.decision}</div>
              <div style={{ fontSize: 14, color: '#111827' }}>Summary: {c.summary?.issue || 'N/A'}</div>
              <div style={{ fontSize: 14, color: '#111827' }}>Citations: {c.citations?.length ? c.citations.join(', ') : 'None'}</div>
              <div style={{ fontSize: 14, color: '#111827' }}>Related Precedents:</div>
              <ul>
                {c.related_precedents?.length ? c.related_precedents.map((p, idx) => (
                  <li key={idx}>{p.case_name} ({p.case_id})</li>
                )) : <li>None</li>}
              </ul>
            </div>
          )) : <div>No cases found.</div>}
        </div>
      )}
    </div>
  )
}