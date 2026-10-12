/**
 * Кастомный тултип при наведении: одна общая стилистика вместо системного title.
 * Рендер в портал поверх всего; позиция подстраивается под границы окна.
 */

import { useState, useRef, useCallback, useLayoutEffect } from 'react'
import { createPortal } from 'react-dom'

const SHOW_DELAY_MS = 500
const HIDE_DELAY_MS = 0
const VIEWPORT_PADDING = 8
const GAP = 6

export default function Tooltip({ children, text, bubbleClassName }) {
  const [visible, setVisible] = useState(false)
  const [coords, setCoords] = useState({ left: 0, top: 0 })
  const [positionReady, setPositionReady] = useState(false)
  const timerRef = useRef(null)
  const hostRef = useRef(null)
  const bubbleRef = useRef(null)

  const clearTimer = useCallback(() => {
    if (timerRef.current) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
  }, [])

  const show = useCallback(() => {
    clearTimer()
    timerRef.current = setTimeout(() => {
      setPositionReady(false)
      setVisible(true)
    }, SHOW_DELAY_MS)
  }, [clearTimer])

  const hide = useCallback(() => {
    clearTimer()
    if (HIDE_DELAY_MS > 0) {
      timerRef.current = setTimeout(() => setVisible(false), HIDE_DELAY_MS)
    } else {
      setVisible(false)
    }
  }, [clearTimer])

  useLayoutEffect(() => {
    if (!visible || !hostRef.current || !bubbleRef.current) return
    const hostRect = hostRef.current.getBoundingClientRect()
    const bubbleRect = bubbleRef.current.getBoundingClientRect()
    const w = window.innerWidth
    const h = window.innerHeight
    const pad = VIEWPORT_PADDING

    const fitsAbove = hostRect.top - GAP - bubbleRect.height >= pad
    const fitsBelow = hostRect.bottom + GAP + bubbleRect.height <= h - pad
    const place = fitsAbove ? 'top' : fitsBelow ? 'bottom' : 'top'

    let top
    if (place === 'top') {
      top = Math.max(pad, hostRect.top - GAP - bubbleRect.height)
    } else {
      top = Math.min(h - pad - bubbleRect.height, hostRect.bottom + GAP)
    }

    let left = hostRect.left + hostRect.width / 2 - bubbleRect.width / 2
    left = Math.max(pad, Math.min(w - pad - bubbleRect.width, left))

    setCoords({ left, top })
    setPositionReady(true)
  }, [visible])

  if (text == null || text === '') return children

  const bubble = (
    <span
      ref={bubbleRef}
      className={['tooltip-bubble', bubbleClassName].filter(Boolean).join(' ')}
      role="tooltip"
      style={{
        position: 'fixed',
        left: positionReady ? coords.left : -9999,
        top: positionReady ? coords.top : -9999,
        visibility: positionReady ? 'visible' : 'hidden',
      }}
    >
      {text}
    </span>
  )

  return (
    <>
      <span
        ref={hostRef}
        className="tooltip-host"
        onMouseEnter={show}
        onMouseLeave={hide}
      >
        {children}
      </span>
      {visible && createPortal(bubble, document.body)}
    </>
  )
}
