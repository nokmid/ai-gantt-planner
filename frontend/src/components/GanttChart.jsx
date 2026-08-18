import React, { useMemo } from 'react'

const DAY_WIDTH = 36
const ROW_HEIGHT = 44
const LABEL_WIDTH = 220
const HEADER_HEIGHT = 48

function parseDate(s) {
  return new Date(s + 'T00:00:00')
}

function daysBetween(a, b) {
  return Math.round((b - a) / (1000 * 60 * 60 * 24))
}

function addDays(date, n) {
  const d = new Date(date)
  d.setDate(d.getDate() + n)
  return d
}

const ASSIGNEE_COLORS = [
  '#6366f1', '#22c55e', '#f59e0b', '#ec4899', '#06b6d4', '#8b5cf6', '#ef4444',
]

function colorForAssignee(name) {
  if (!name) return '#94a3b8'
  let hash = 0
  for (let i = 0; i < name.length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash)
  return ASSIGNEE_COLORS[Math.abs(hash) % ASSIGNEE_COLORS.length]
}

export default function GanttChart({ tasks, onTaskClick, highlightIds = [] }) {
  const { minDate, totalDays, taskIndex } = useMemo(() => {
    if (tasks.length === 0) return { minDate: new Date(), totalDays: 0, taskIndex: {} }
    const starts = tasks.map((t) => parseDate(t.start_date))
    const ends = tasks.map((t) => addDays(parseDate(t.start_date), t.duration_days))
    const minDate = new Date(Math.min(...starts))
    const maxDate = new Date(Math.max(...ends))
    const totalDays = Math.max(daysBetween(minDate, maxDate) + 2, 7)
    const taskIndex = Object.fromEntries(tasks.map((t, i) => [t.id, i]))
    return { minDate, totalDays, taskIndex }
  }, [tasks])

  if (tasks.length === 0) {
    return <div className="gantt-empty">Нет задач для отображения. Загрузите Excel или добавьте задачу через чат.</div>
  }

  const chartWidth = LABEL_WIDTH + totalDays * DAY_WIDTH
  const chartHeight = HEADER_HEIGHT + tasks.length * ROW_HEIGHT

  const dayHeaders = []
  for (let i = 0; i < totalDays; i++) {
    const d = addDays(minDate, i)
    dayHeaders.push(d)
  }

  const today = new Date()
  today.setHours(0, 0, 0, 0)
  const todayOffset = daysBetween(minDate, today)

  return (
    <div className="gantt-scroll">
      <svg width={chartWidth} height={chartHeight} className="gantt-svg">
        {/* фон недель/выходных */}
        {dayHeaders.map((d, i) => {
          const isWeekend = d.getDay() === 0 || d.getDay() === 6
          return isWeekend ? (
            <rect
              key={`we-${i}`}
              x={LABEL_WIDTH + i * DAY_WIDTH}
              y={0}
              width={DAY_WIDTH}
              height={chartHeight}
              fill="var(--gantt-weekend)"
            />
          ) : null
        })}

        {/* линия "сегодня" */}
        {todayOffset >= 0 && todayOffset < totalDays && (
          <line
            x1={LABEL_WIDTH + todayOffset * DAY_WIDTH}
            y1={0}
            x2={LABEL_WIDTH + todayOffset * DAY_WIDTH}
            y2={chartHeight}
            stroke="var(--gantt-today)"
            strokeWidth={2}
            strokeDasharray="4,3"
          />
        )}

        {/* заголовок дат */}
        {dayHeaders.map((d, i) => (
          <text
            key={`h-${i}`}
            x={LABEL_WIDTH + i * DAY_WIDTH + DAY_WIDTH / 2}
            y={HEADER_HEIGHT - 10}
            textAnchor="middle"
            fontSize="11"
            fill="var(--gantt-text-muted)"
          >
            {d.getDate()}.{d.getMonth() + 1}
          </text>
        ))}
        <line x1={0} y1={HEADER_HEIGHT} x2={chartWidth} y2={HEADER_HEIGHT} stroke="var(--gantt-grid)" />

        {/* строки задач + зависимости */}
        {tasks.map((t, rowIdx) => {
          const y = HEADER_HEIGHT + rowIdx * ROW_HEIGHT
          return (
            <g key={`row-${t.id}`}>
              <line x1={0} y1={y + ROW_HEIGHT} x2={chartWidth} y2={y + ROW_HEIGHT} stroke="var(--gantt-grid)" />
              <text x={12} y={y + ROW_HEIGHT / 2 + 4} fontSize="13" fill="var(--gantt-text)">
                {t.name.length > 26 ? t.name.slice(0, 25) + '…' : t.name}
              </text>
            </g>
          )
        })}

        {/* стрелки зависимостей */}
        {tasks.map((t) => {
          const toRow = taskIndex[t.id]
          const toX = LABEL_WIDTH + daysBetween(minDate, parseDate(t.start_date)) * DAY_WIDTH
          const toY = HEADER_HEIGHT + toRow * ROW_HEIGHT + ROW_HEIGHT / 2
          return t.predecessors.map((predId) => {
            const fromRow = taskIndex[predId]
            if (fromRow === undefined) return null
            const pred = tasks[fromRow]
            const fromX = LABEL_WIDTH + (daysBetween(minDate, parseDate(pred.start_date)) + pred.duration_days) * DAY_WIDTH
            const fromY = HEADER_HEIGHT + fromRow * ROW_HEIGHT + ROW_HEIGHT / 2
            const midX = fromX + Math.max(10, (toX - fromX) / 2)
            const path = `M ${fromX} ${fromY} L ${midX} ${fromY} L ${midX} ${toY} L ${toX} ${toY}`
            return (
              <path
                key={`dep-${predId}-${t.id}`}
                d={path}
                fill="none"
                stroke="var(--gantt-dep)"
                strokeWidth={1.5}
                markerEnd="url(#arrow)"
              />
            )
          })
        })}

        <defs>
          <marker id="arrow" markerWidth="8" markerHeight="8" refX="6" refY="3" orient="auto">
            <path d="M0,0 L0,6 L6,3 z" fill="var(--gantt-dep)" />
          </marker>
        </defs>

        {/* бары задач */}
        {tasks.map((t, rowIdx) => {
          const y = HEADER_HEIGHT + rowIdx * ROW_HEIGHT + 8
          const x = LABEL_WIDTH + daysBetween(minDate, parseDate(t.start_date)) * DAY_WIDTH
          const width = Math.max(t.duration_days * DAY_WIDTH - 4, 8)
          const color = colorForAssignee(t.assignee)
          const isHighlighted = highlightIds.includes(t.id)
          return (
            <g
              key={`bar-${t.id}`}
              className="gantt-bar-group"
              onClick={() => onTaskClick(t)}
              style={{ cursor: 'pointer' }}
            >
              <rect
                x={x}
                y={y}
                width={width}
                height={ROW_HEIGHT - 16}
                rx={6}
                fill={color}
                opacity={isHighlighted ? 1 : 0.85}
                stroke={isHighlighted ? 'var(--gantt-highlight)' : 'none'}
                strokeWidth={isHighlighted ? 3 : 0}
              />
              <rect
                x={x}
                y={y}
                width={(width * t.progress) / 100}
                height={ROW_HEIGHT - 16}
                rx={6}
                fill="rgba(255,255,255,0.35)"
              />
              {width > 40 && (
                <text x={x + 8} y={y + (ROW_HEIGHT - 16) / 2 + 4} fontSize="11" fill="#fff" fontWeight="500">
                  {t.assignee || '—'}
                </text>
              )}
            </g>
          )
        })}
      </svg>
    </div>
  )
}
