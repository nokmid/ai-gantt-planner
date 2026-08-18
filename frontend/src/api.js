const BASE = (import.meta.env.VITE_API_BASE_URL || '') + '/api'

async function handle(res) {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Ошибка запроса: ${res.status}`)
  }
  return res.json()
}

export const api = {
  listTasks: () => fetch(`${BASE}/tasks`).then(handle),

  patchTask: (id, fields) =>
    fetch(`${BASE}/tasks/${id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(fields),
    }).then(handle),

  deleteTask: (id) => fetch(`${BASE}/tasks/${id}`, { method: 'DELETE' }).then(handle),

  sendChatMessage: (message) =>
    fetch(`${BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message }),
    }).then(handle),

  resetChat: () => fetch(`${BASE}/chat/reset`, { method: 'POST' }).then(handle),

  importExcel: (file) => {
    const form = new FormData()
    form.append('file', file)
    return fetch(`${BASE}/excel/import`, { method: 'POST', body: form }).then(handle)
  },

  exportExcelUrl: () => `${BASE}/excel/export`,
}
