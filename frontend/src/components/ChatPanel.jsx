import React, { useEffect, useRef, useState } from 'react'
import { api } from '../api'

const SUGGESTIONS = [
  'Перенеси "Дизайн UI" на 2 дня позже',
  'Назначь Смирнову на Backend API',
  'Добавь задачу "Ретро" после Релиза, 1 день',
]

export default function ChatPanel({ onTasksUpdated, onHighlight }) {
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'Привет! Я могу переносить задачи, менять исполнителей, добавлять зависимости и новые задачи. Просто напишите, что нужно сделать.' },
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const scrollRef = useRef(null)

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text) => {
    const msg = (text ?? input).trim()
    if (!msg || loading) return
    setMessages((m) => [...m, { role: 'user', text: msg }])
    setInput('')
    setLoading(true)
    setError(null)
    try {
      const res = await api.sendChatMessage(msg)
      setMessages((m) => [...m, { role: 'assistant', text: res.reply, toolCalls: res.tool_calls }])
      onTasksUpdated(res.tasks)
      const touchedIds = (res.tool_calls || [])
        .map((c) => c.result?.task?.id)
        .filter(Boolean)
      onHighlight(touchedIds)
    } catch (e) {
      setError(e.message)
      setMessages((m) => [...m, { role: 'assistant', text: 'Не получилось выполнить запрос: ' + e.message, isError: true }])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">Чат-редактор плана</div>

      <div className="chat-messages" ref={scrollRef}>
        {messages.map((m, i) => (
          <div key={i} className={`chat-msg chat-msg-${m.role} ${m.isError ? 'chat-msg-error' : ''}`}>
            <div className="chat-bubble">{m.text}</div>
            {m.toolCalls && m.toolCalls.length > 0 && (
              <details className="chat-tool-log">
                <summary>{m.toolCalls.length} действий с планом</summary>
                <ul>
                  {m.toolCalls.map((c, j) => (
                    <li key={j}><code>{c.tool}</code>({JSON.stringify(c.input)})</li>
                  ))}
                </ul>
              </details>
            )}
          </div>
        ))}
        {loading && <div className="chat-msg chat-msg-assistant"><div className="chat-bubble chat-typing">думаю…</div></div>}
      </div>

      {messages.length <= 1 && (
        <div className="chat-suggestions">
          {SUGGESTIONS.map((s) => (
            <button key={s} className="suggestion-chip" onClick={() => send(s)}>{s}</button>
          ))}
        </div>
      )}

      <form className="chat-input-row" onSubmit={(e) => { e.preventDefault(); send() }}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Например: перенеси Backend API на неделю позже"
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>Отправить</button>
      </form>
    </div>
  )
}
