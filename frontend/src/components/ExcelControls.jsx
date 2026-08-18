import React, { useRef, useState } from 'react'
import { api } from '../api'

export default function ExcelControls({ onImported }) {
  const fileRef = useRef(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState(null)

  const handleFile = async (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setBusy(true)
    setError(null)
    try {
      const res = await api.importExcel(file)
      onImported(res.tasks)
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
      e.target.value = ''
    }
  }

  return (
    <div className="excel-controls">
      <button className="btn" onClick={() => fileRef.current?.click()} disabled={busy}>
        {busy ? 'Загрузка…' : '📤 Загрузить Excel'}
      </button>
      <input ref={fileRef} type="file" accept=".xlsx" hidden onChange={handleFile} />
      <a className="btn" href={api.exportExcelUrl()}>📥 Экспорт в Excel</a>
      {error && <span className="error-text">{error}</span>}
    </div>
  )
}
