import React, { useState } from 'react'

export default function TaskModal({ task, allTasks, onClose, onSave, onDelete }) {
  const [form, setForm] = useState({
    name: task.name,
    description: task.description,
    assignee: task.assignee,
    start_date: task.start_date,
    duration_days: task.duration_days,
    progress: task.progress,
  })

  if (!task) return null

  const predecessorTasks = allTasks.filter((t) => task.predecessors.includes(t.id))
  const dependents = allTasks.filter((t) => t.predecessors.includes(task.id))

  const handleChange = (field, value) => setForm((f) => ({ ...f, [field]: value }))

  const handleSave = () => {
    onSave(task.id, {
      ...form,
      duration_days: Number(form.duration_days),
      progress: Number(form.progress),
    })
    onClose()
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h3>Детали задачи</h3>
          <button className="icon-btn" onClick={onClose}>✕</button>
        </div>

        <label className="field">
          <span>Название</span>
          <input value={form.name} onChange={(e) => handleChange('name', e.target.value)} />
        </label>

        <label className="field">
          <span>Описание</span>
          <textarea rows={3} value={form.description} onChange={(e) => handleChange('description', e.target.value)} />
        </label>

        <div className="field-row">
          <label className="field">
            <span>Исполнитель</span>
            <input value={form.assignee} onChange={(e) => handleChange('assignee', e.target.value)} />
          </label>
          <label className="field">
            <span>Дата начала</span>
            <input type="date" value={form.start_date} onChange={(e) => handleChange('start_date', e.target.value)} />
          </label>
        </div>

        <div className="field-row">
          <label className="field">
            <span>Длительность (дней)</span>
            <input type="number" min={1} value={form.duration_days} onChange={(e) => handleChange('duration_days', e.target.value)} />
          </label>
          <label className="field">
            <span>Прогресс: {form.progress}%</span>
            <input type="range" min={0} max={100} value={form.progress} onChange={(e) => handleChange('progress', e.target.value)} />
          </label>
        </div>

        <div className="field">
          <span>Зависит от (предшественники)</span>
          <div className="chip-list">
            {predecessorTasks.length ? predecessorTasks.map((t) => (
              <span key={t.id} className="chip">{t.name}</span>
            )) : <span className="muted">нет</span>}
          </div>
        </div>

        <div className="field">
          <span>От этой задачи зависят</span>
          <div className="chip-list">
            {dependents.length ? dependents.map((t) => (
              <span key={t.id} className="chip chip-secondary">{t.name}</span>
            )) : <span className="muted">нет</span>}
          </div>
        </div>

        <div className="modal-actions">
          <button className="btn btn-danger" onClick={() => { onDelete(task.id); onClose() }}>Удалить</button>
          <button className="btn btn-primary" onClick={handleSave}>Сохранить</button>
        </div>
      </div>
    </div>
  )
}
