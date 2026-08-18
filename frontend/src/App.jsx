import React, { useEffect, useState } from 'react'
import GanttChart from './components/GanttChart.jsx'
import ChatPanel from './components/ChatPanel.jsx'
import TaskModal from './components/TaskModal.jsx'
import ExcelControls from './components/ExcelControls.jsx'
import { api } from './api'

export default function App() {
  const [tasks, setTasks] = useState([])
  const [selectedTask, setSelectedTask] = useState(null)
  const [highlightIds, setHighlightIds] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listTasks()
      .then(setTasks)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (highlightIds.length === 0) return
    const timer = setTimeout(() => setHighlightIds([]), 2500)
    return () => clearTimeout(timer)
  }, [highlightIds])

  const handleSaveTask = async (id, fields) => {
    const updated = await api.patchTask(id, fields)
    setTasks((ts) => ts.map((t) => (t.id === id ? updated : t)))
  }

  const handleDeleteTask = async (id) => {
    await api.deleteTask(id)
    setTasks((ts) => ts.filter((t) => t.id !== id))
  }

  return (
    <div className="app-layout">
      <header className="app-header">
        <h1>AI Gantt Planner</h1>
        <ExcelControls onImported={setTasks} />
      </header>

      <main className="app-main">
        <section className="gantt-section">
          {loading && <div className="loading">Загрузка плана…</div>}
          {error && <div className="error-banner">Ошибка: {error}</div>}
          {!loading && !error && (
            <GanttChart tasks={tasks} onTaskClick={setSelectedTask} highlightIds={highlightIds} />
          )}
        </section>

        <aside className="chat-section">
          <ChatPanel onTasksUpdated={setTasks} onHighlight={setHighlightIds} />
        </aside>
      </main>

      {selectedTask && (
        <TaskModal
          task={selectedTask}
          allTasks={tasks}
          onClose={() => setSelectedTask(null)}
          onSave={handleSaveTask}
          onDelete={handleDeleteTask}
        />
      )}
    </div>
  )
}
