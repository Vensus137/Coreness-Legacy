/**
 * Таб-бар воркспейсов: неактивные с фоном заголовка, hover как в сайдбаре, активная доходит до контента.
 * Между вкладками — разделитель. Прокрутка колёсиком. Скроллбар кастомный, поверх вкладок (как в VS Code).
 */

import { useRef, Fragment, useState, useEffect, useCallback } from 'react'
import { IconPlus, IconX } from './Icons'
import Tooltip from './Tooltip'

const DRAG_THRESHOLD_PX = 5

export default function TabBar({
  workspaces,
  activeIndex,
  onSelect,
  onAdd,
  onClose,
  onReorder,
  onTabRename,
  editingTabIndex,
  setEditingTabIndex,
  tabContextMenuItems = [],
  onTabContextMenuItemClick,
  tabAttentionIds = [],
}) {
  const scrollRef = useRef(null)
  const tabRefs = useRef([])
  /** Ширины вкладок в обычном режиме (label), чтобы при переименовании не менять размер — не двигать соседние */
  const tabWidthsRef = useRef({})
  const editInputRef = useRef(null)
  const contextMenuRef = useRef(null)
  const dragStartRef = useRef(null)
  const dropIndicatorRef = useRef(null)
  const didDragRef = useRef(false)
  const hadDragRef = useRef(false)
  /** Индекс вкладки, на которой закончился drop — подавляем только клик по ней, не по другим. */
  const droppedTabIndexRef = useRef(null)
  const [scroll, setScroll] = useState({ left: 0, width: 0, scrollWidth: 0 })
  const [dragging, setDragging] = useState(false)
  const [dragStartIndex, setDragStartIndex] = useState(null)
  const [dragTabIndex, setDragTabIndex] = useState(null)
  const [dropIndicatorIndex, setDropIndicatorIndex] = useState(null)
  const [contextMenu, setContextMenu] = useState({ index: -1, x: 0, y: 0 })
  const [editingTabWidth, setEditingTabWidth] = useState(null)
  const isChatTab = (w) => w?.kind === 'chat'

  const updateScroll = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setScroll({
      left: el.scrollLeft,
      width: el.clientWidth,
      scrollWidth: el.scrollWidth,
    })
  }, [])

  useEffect(() => {
    updateScroll()
  }, [workspaces, updateScroll])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const ro = new ResizeObserver(updateScroll)
    ro.observe(el)
    el.addEventListener('scroll', updateScroll)
    return () => {
      ro.disconnect()
      el.removeEventListener('scroll', updateScroll)
    }
  }, [updateScroll])

  useEffect(() => {
    const tabEl = tabRefs.current[activeIndex]
    if (tabEl) {
      tabEl.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'nearest' })
    }
  }, [activeIndex])

  // Сохраняем ширину вкладок в обычном режиме, чтобы при переименовании подставить её и не сдвигать соседние
  useEffect(() => {
    workspaces.forEach((_, i) => {
      if (i === editingTabIndex) return
      const el = tabRefs.current[i]
      if (el) tabWidthsRef.current[i] = el.offsetWidth
    })
  })

  useEffect(() => {
    if (editingTabIndex == null) {
      setEditingTabWidth(null)
      return
    }
    // Берём ширину из сохранённой (до переключения на input), иначе вкладка уже могла растянуться; fallback — из DOM
    const w = tabWidthsRef.current[editingTabIndex] ?? tabRefs.current[editingTabIndex]?.offsetWidth
    if (w != null) setEditingTabWidth(w)
    editInputRef.current?.focus()
    editInputRef.current?.select()
  }, [editingTabIndex])

  useEffect(() => {
    if (contextMenu.index < 0) return
    const close = (e) => {
      if (contextMenuRef.current && contextMenuRef.current.contains(e.target)) return
      setContextMenu((c) => ({ ...c, index: -1 }))
    }
    document.addEventListener('mousedown', close)
    return () => document.removeEventListener('mousedown', close)
  }, [contextMenu.index])

  useEffect(() => {
    if (dragStartIndex == null) return
    const move = (e) => {
      const start = dragStartRef.current
      if (!start) return
      const dx = e.clientX - start.x
      const dy = e.clientY - start.y
      const dist = Math.sqrt(dx * dx + dy * dy)
      const pastThreshold = dist >= DRAG_THRESHOLD_PX
      setDragTabIndex((prev) => {
        if (prev != null) return prev
        if (pastThreshold) {
          hadDragRef.current = true
          return start.index
        }
        return null
      })
      if (!pastThreshold && !hadDragRef.current) return
      const refs = tabRefs.current
      const n = workspaces.length
      let indicator = null
      if (n > 0) {
        const cursorX = e.clientX
        for (let i = 0; i < n; i++) {
          const el = refs[i]
          if (!el) continue
          const r = el.getBoundingClientRect()
          if (cursorX < r.left) {
            indicator = i
            break
          }
          if (cursorX < r.right) {
            indicator = cursorX < (r.left + r.right) / 2 ? i : i + 1
            break
          }
        }
        if (indicator === null) indicator = n
      }
      dropIndicatorRef.current = indicator
      setDropIndicatorIndex(indicator)
    }
    const up = () => {
      const from = dragStartRef.current?.index ?? null
      const dropAt = dropIndicatorRef.current
      const toIndex = from != null && dropAt != null ? (dropAt <= from ? dropAt : dropAt - 1) : null
      setDragStartIndex(null)
      setDragTabIndex(null)
      setDropIndicatorIndex(null)
      dragStartRef.current = null
      dropIndicatorRef.current = null
      if (hadDragRef.current) {
        didDragRef.current = true
        hadDragRef.current = false
        droppedTabIndexRef.current = toIndex ?? from
      }
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
      if (from != null && dropAt != null && onReorder) {
        if (toIndex !== from) {
          onReorder(from, toIndex)
        }
      }
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
    return () => {
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
    }
  }, [dragStartIndex, workspaces.length, onReorder])

  const handleWheel = (e) => {
    const el = scrollRef.current
    if (!el || el.scrollWidth <= el.clientWidth) return
    e.preventDefault()
    el.scrollLeft += e.deltaY
  }

  const isScrollable = scroll.scrollWidth > scroll.width
  const maxScroll = scroll.scrollWidth - scroll.width
  const thumbWidth = isScrollable && scroll.scrollWidth > 0
    ? Math.max(24, (scroll.width * scroll.width) / scroll.scrollWidth)
    : 0
  const thumbLeft = isScrollable && maxScroll > 0
    ? (scroll.left / maxScroll) * (scroll.width - thumbWidth)
    : 0

  const handleTrackClick = (e) => {
    const el = scrollRef.current
    const track = e.currentTarget
    if (!el || !isScrollable) return
    const rect = track.getBoundingClientRect()
    const x = e.clientX - rect.left
    const clickPos = x / rect.width
    el.scrollLeft = clickPos * (el.scrollWidth - el.clientWidth)
  }

  const handleThumbMouseDown = (e) => {
    e.preventDefault()
    if (!isScrollable) return
    setDragging(true)
    const el = scrollRef.current
    const startX = e.clientX
    const startLeft = el.scrollLeft
    const move = (e2) => {
      const dx = e2.clientX - startX
      const ratio = el.scrollWidth / el.clientWidth
      el.scrollLeft = startLeft + dx * ratio
    }
    const up = () => {
      setDragging(false)
      document.removeEventListener('mousemove', move)
      document.removeEventListener('mouseup', up)
    }
    document.addEventListener('mousemove', move)
    document.addEventListener('mouseup', up)
  }

  return (
    <div className={`tab-bar-wrap ${dragTabIndex != null ? 'tab-bar-wrap--dragging' : ''}`}>
      <div ref={scrollRef} className="tab-bar" onWheel={handleWheel}>
        {workspaces.map((w, i) => (
          <Fragment key={w.id}>
            {i > 0 && <span className="tab-sep" aria-hidden />}
            {dropIndicatorIndex === i && <span className="tab-drop-indicator" aria-hidden />}
            <div
              ref={(el) => { tabRefs.current[i] = el }}
              className={`tab ${i === activeIndex ? 'tab--active' : ''} ${editingTabIndex === i ? 'tab--editing' : ''} ${dragTabIndex === i ? 'tab--drag-source' : ''} ${tabAttentionIds.includes(w.id) ? 'tab--attention' : ''}`}
              style={editingTabIndex === i && editingTabWidth != null ? { width: editingTabWidth } : undefined}
              onMouseDown={(e) => {
                if (e.button !== 0 || editingTabIndex === i) return
                if (e.target.closest('.tab-close')) return
                hadDragRef.current = false
                dragStartRef.current = { index: i, x: e.clientX, y: e.clientY }
                setDragStartIndex(i)
              }}
              onClick={(e) => {
                if (editingTabIndex === i) return
                e.stopPropagation()
                if (didDragRef.current) {
                  didDragRef.current = false
                  if (i === droppedTabIndexRef.current) return
                  droppedTabIndexRef.current = null
                }
                onSelect(i)
              }}
              onContextMenu={(e) => {
                if (isChatTab(w)) {
                  e.preventDefault()
                  setContextMenu({ index: i, x: e.clientX, y: e.clientY })
                }
              }}
            >
              {editingTabIndex === i ? (
                <input
                  ref={editInputRef}
                  type="text"
                  className="tab-label-edit"
                  defaultValue={w.title}
                  onClick={(e) => e.stopPropagation()}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      e.preventDefault()
                      onTabRename(i, e.target.value)
                    }
                    if (e.key === 'Escape') {
                      e.preventDefault()
                      setEditingTabIndex(null)
                    }
                  }}
                  onBlur={(e) => {
                    const v = e.target.value?.trim()
                    if (v) onTabRename(i, v)
                    else setEditingTabIndex(null)
                  }}
                  aria-label="Название чата"
                />
              ) : (
                <>
                  <span className="tab-label">{w.title}</span>
                  {workspaces.length > 1 && (
                    <Tooltip text="Закрыть">
                      <span
                        className="tab-close"
                        role="button"
                        tabIndex={0}
                        onClick={(e) => {
                          e.stopPropagation()
                          onClose(i)
                        }}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault()
                            onClose(i)
                          }
                        }}
                        aria-label="Закрыть"
                      >
                        <IconX />
                      </span>
                    </Tooltip>
                  )}
                </>
              )}
            </div>
          </Fragment>
        ))}
        {dropIndicatorIndex === workspaces.length && <span className="tab-drop-indicator" aria-hidden />}
        <span className="tab-sep" aria-hidden />
        <Tooltip text="Новый чат">
          <button type="button" className="tab tab-add" onClick={onAdd} aria-label="Новый чат">
            <IconPlus />
          </button>
        </Tooltip>
      </div>
      {contextMenu.index >= 0 && (
        <div
          ref={contextMenuRef}
          className="app-dropdown app-dropdown--fixed"
          style={{ left: contextMenu.x, top: contextMenu.y }}
          role="menu"
        >
          {tabContextMenuItems.map((item) => (
            <button
              key={item.builtIn ? item.id : `${item.pluginId}_${item.id}`}
              type="button"
              className="app-dropdown-item"
              onClick={() => {
                setContextMenu((c) => ({ ...c, index: -1 }))
                onTabContextMenuItemClick?.(item, contextMenu.index)
              }}
              role="menuitem"
            >
              {item.label}
            </button>
          ))}
        </div>
      )}
      {isScrollable && (
        <div
          className="tab-bar-scrollbar-overlay"
          role="scrollbar"
          aria-valuenow={scroll.scrollWidth > 0 ? Math.round((scroll.left / (scroll.scrollWidth - scroll.width)) * 100) : 0}
          aria-valuemin={0}
          aria-valuemax={100}
        >
          <div
            className="tab-bar-scrollbar-track"
            onClick={handleTrackClick}
          >
            <div
              className={`tab-bar-scrollbar-thumb ${dragging ? 'tab-bar-scrollbar-thumb--dragging' : ''}`}
              style={{ width: thumbWidth, transform: `translateX(${thumbLeft}px)` }}
              onMouseDown={handleThumbMouseDown}
            />
          </div>
        </div>
      )}
    </div>
  )
}
