/**
 * Универсальное модальное окно в стиле темы: оверлей, панель с заголовком и контентом. Escape закрывает.
 */

import { useState, useEffect, useRef } from 'react'
import Tooltip from './Tooltip'

const COPIED_RESET_MS = 1500

export default function Modal({ open, onClose, title, children, variant = 'default', copyText, panelClassName }) {
  const panelRef = useRef(null)
  const [copied, setCopied] = useState(false)
  const copyTimeoutRef = useRef(null)
  const panelClass = ['modal-panel', panelClassName].filter(Boolean).join(' ')

  const handleCopy = (e) => {
    if (copyText && navigator.clipboard?.writeText) {
      navigator.clipboard.writeText(copyText)
      setCopied(true)
      e?.currentTarget?.blur()
      if (copyTimeoutRef.current) clearTimeout(copyTimeoutRef.current)
      copyTimeoutRef.current = setTimeout(() => {
        setCopied(false)
        copyTimeoutRef.current = null
      }, COPIED_RESET_MS)
    }
  }

  useEffect(() => {
    if (!open) {
      setCopied(false)
      if (copyTimeoutRef.current) {
        clearTimeout(copyTimeoutRef.current)
        copyTimeoutRef.current = null
      }
    }
  }, [open])

  useEffect(() => {
    if (!open) return
    const handleEscape = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleEscape)
    return () => document.removeEventListener('keydown', handleEscape)
  }, [open, onClose])

  // Фокус при открытии не ставим — иначе у крестика сразу виден ореол; при навигации с клавиатуры outline даёт :focus-visible
  // useEffect(() => { if (open && panelRef.current) { ... focus() } }, [open]) — убрано

  if (!open) return null

  return (
    <div
      className={`modal-overlay modal-overlay--${variant}`}
      onClick={(e) => e.target === e.currentTarget && onClose()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div ref={panelRef} className={panelClass}>
        <div className="modal-header">
          <h2 id="modal-title" className="modal-title">
            {title}
          </h2>
          <div className="modal-header-actions">
            {copyText != null && (
              copied ? (
                <button
                  type="button"
                  className="modal-copy modal-copy--done"
                  aria-label="Скопировано"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                    <path d="M20 6L9 17l-5-5" />
                  </svg>
                </button>
              ) : (
                <Tooltip text="Копировать">
                  <button
                    type="button"
                    className="modal-copy"
                    onClick={handleCopy}
                    aria-label="Копировать"
                  >
                    <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
                      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
                    </svg>
                  </button>
                </Tooltip>
              )
            )}
            <Tooltip text="Закрыть">
              <button
                type="button"
                className="modal-close"
                onClick={onClose}
                aria-label="Закрыть"
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M18 6L6 18M6 6l12 12" />
                </svg>
              </button>
            </Tooltip>
          </div>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  )
}
