/**
 * Экран чата: список сообщений и панель ввода. Общий шаблон WorkspaceLayout (скролл скраю, footer = ввод).
 * Пузырь только у сообщений пользователя; user/system — структура + ссылки, assistant/auto — markdown.
 */

import { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react'
import { SimpleMessageContent, MarkdownMessageContent } from './ChatMessageContent'
import Modal from './Modal'
import Tooltip from './Tooltip'
import { WorkspaceLayout } from '../contributions/workspace'

function DownloadIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M12 15V3" />
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="m7 10 5 5 5-5" />
    </svg>
  )
}

function CopyIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <rect width="14" height="14" x="8" y="8" rx="2" ry="2" />
      <path d="M4 16c-1.1 0-2-.9-2-2V4c0-1.1.9-2 2-2h10c1.1 0 2 .9 2 2" />
    </svg>
  )
}

function CheckIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <path d="M20 6L9 17l-5-5" />
    </svg>
  )
}

function InfoIcon() {
  return (
    <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
      <circle cx="12" cy="12" r="10" />
      <path d="M12 16v-4" />
      <path d="M12 8h.01" />
    </svg>
  )
}

/** Панель действий под сообщением assistant/auto: скачать, скопировать, инфо. */
function MessageActions({ text, meta }) {
  const [copied, setCopied] = useState(false)
  const [downloaded, setDownloaded] = useState(false)

  const handleCopy = useCallback(() => {
    navigator.clipboard?.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1500)
    })
  }, [text])

  const handleDownload = useCallback(() => {
    const words = text.trim().split(/\s+/).slice(0, 6).join('_').replace(/[^\wа-яёА-ЯЁ-]/gi, '').slice(0, 48)
    const filename = words ? `${words}.md` : 'message.md'
    const blob = new Blob([text], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    setDownloaded(true)
    setTimeout(() => setDownloaded(false), 1500)
  }, [text])

  const metaText = meta ? JSON.stringify(meta, null, 2) : null

  return (
    <div className="chat-message-actions">
      <Tooltip text={downloaded ? null : 'Скачать как Markdown'}>
        <button
          type="button"
          className="chat-message-action-btn"
          onClick={handleDownload}
          disabled={downloaded}
          aria-label="Скачать сообщение"
        >
          <DownloadIcon />
        </button>
      </Tooltip>
      <Tooltip text={copied ? 'Скопировано' : 'Копировать'}>
        <button
          type="button"
          className="chat-message-action-btn"
          onClick={handleCopy}
          aria-label="Копировать сообщение"
        >
          {copied ? <CheckIcon /> : <CopyIcon />}
        </button>
      </Tooltip>
      {metaText && (
        <Tooltip text={metaText} bubbleClassName="tooltip-bubble--multiline">
          <span className="chat-message-action-info" aria-label="Метаинформация о сообщении">
            <InfoIcon />
          </span>
        </Tooltip>
      )}
    </div>
  )
}

const INPUT_MAX_HEIGHT = 280
const INPUT_MIN_HEIGHT = 25

const SCROLL_AT_BOTTOM_THRESHOLD = 80
const SCROLL_TO_BOTTOM_BUTTON_THRESHOLD = 800
const SCROLL_FOLLOW_FACTOR = 0.25

export default function ChatView({ messages, removingMessageIndices = new Set(), onSend, onClearChat, isLoading = false, onMessageDrawComplete }) {
  const [input, setInput] = useState('')
  const [confirmClearOpen, setConfirmClearOpen] = useState(false)
  const [expandedIndices, setExpandedIndices] = useState(() => new Set())
  const [messageMeta, setMessageMeta] = useState(() => ({ overflow: new Set(), measured: new Set() }))
  const [showScrollToBottom, setShowScrollToBottom] = useState(false)
  const bottomRef = useRef(null)
  const scrollContainerRef = useRef(null)
  const messagesContainerRef = useRef(null)
  const userScrolledUpRef = useRef(false)
  const scrollAnimationRef = useRef(null)
  const isAnimatingScrollRef = useRef(false)
  const inputRef = useRef(null)
  const contentRefs = useRef({})
  const prevMessageCountRef = useRef(0)
  const animateScrollToBottomRef = useRef(null)
  const showScrollToBottomRef = useRef(false)

  // Один триггер: при росте числа сообщений — скролл вниз, если пользователь у низа или сообщение от пользователя
  useLayoutEffect(() => {
    if (messages.length > prevMessageCountRef.current && prevMessageCountRef.current > 0) {
      const lastMsg = messages[messages.length - 1]
      const fromUser = lastMsg?.sender === 'user'
      const shouldScroll = fromUser || !userScrolledUpRef.current
      prevMessageCountRef.current = messages.length
      if (shouldScroll) {
        userScrolledUpRef.current = false
        const fn = animateScrollToBottomRef.current
        if (fn) fn()
        else bottomRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' })
      }
    } else if (messages.length > 0 && prevMessageCountRef.current === 0) {
      prevMessageCountRef.current = messages.length
      bottomRef.current?.scrollIntoView({ behavior: 'auto', block: 'end' })
    } else {
      prevMessageCountRef.current = messages.length
    }
  }, [messages])

  useEffect(() => {
    const scrollEl = scrollContainerRef.current
    const contentEl = messagesContainerRef.current
    if (!scrollEl || !contentEl) return

    const onScroll = () => {
      const { scrollTop, scrollHeight, clientHeight } = scrollEl
      const distanceFromBottom = scrollHeight - scrollTop - clientHeight
      const atBottom = distanceFromBottom <= SCROLL_AT_BOTTOM_THRESHOLD
      userScrolledUpRef.current = !atBottom
      const hasScroll = scrollHeight > clientHeight
      const showBtn = hasScroll && distanceFromBottom > SCROLL_TO_BOTTOM_BUTTON_THRESHOLD
      if (showScrollToBottomRef.current !== showBtn) {
        showScrollToBottomRef.current = showBtn
        setShowScrollToBottom(showBtn)
      }
      if (!atBottom && isAnimatingScrollRef.current) {
        if (scrollAnimationRef.current != null) cancelAnimationFrame(scrollAnimationRef.current)
        scrollAnimationRef.current = null
        isAnimatingScrollRef.current = false
      }
    }
    scrollEl.addEventListener('scroll', onScroll, { passive: true })
    onScroll()

    const animateScrollToBottom = () => {
      if (scrollAnimationRef.current != null) return
      isAnimatingScrollRef.current = true
      const step = () => {
        const targetTop = scrollEl.scrollHeight - scrollEl.clientHeight
        const current = scrollEl.scrollTop
        if (targetTop - current <= 2) {
          scrollEl.scrollTop = targetTop
          scrollAnimationRef.current = null
          isAnimatingScrollRef.current = false
          userScrolledUpRef.current = false
          return
        }
        scrollEl.scrollTop = current + (targetTop - current) * SCROLL_FOLLOW_FACTOR
        scrollAnimationRef.current = requestAnimationFrame(step)
      }
      scrollAnimationRef.current = requestAnimationFrame(step)
    }
    animateScrollToBottomRef.current = animateScrollToBottom

    const ro = new ResizeObserver(() => {
      onScroll()
      if (isAnimatingScrollRef.current || userScrolledUpRef.current) return
      // При изменении размера контента просто привязываемся к низу без анимации — иначе при открытии чата виден короткий «просад» на десятки пикселей
      const targetTop = scrollEl.scrollHeight - scrollEl.clientHeight
      scrollEl.scrollTop = targetTop
    })
    ro.observe(contentEl)

    return () => {
      scrollEl.removeEventListener('scroll', onScroll)
      if (scrollAnimationRef.current != null) cancelAnimationFrame(scrollAnimationRef.current)
      ro.disconnect()
    }
  }, [])

  useEffect(() => {
    setMessageMeta((prev) => {
      const nextOverflow = new Set()
      const nextMeasured = new Set(prev.measured)
      messages.forEach((m, i) => {
        if (m.sender !== 'user') return
        if (expandedIndices.has(i)) {
          if (prev.overflow.has(i)) nextOverflow.add(i)
          return
        }
        const el = contentRefs.current[i]
        if (el) {
          nextMeasured.add(i)
          if (el.scrollHeight > el.clientHeight) nextOverflow.add(i)
        }
      })
      return { overflow: nextOverflow, measured: nextMeasured }
    })
  }, [messages, expandedIndices])

  const toggleExpanded = (i) => {
    setExpandedIndices((prev) => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  const adjustInputHeight = () => {
    const el = inputRef.current
    if (!el) return
    el.style.height = 'auto'
    const h = Math.max(INPUT_MIN_HEIGHT, Math.min(el.scrollHeight, INPUT_MAX_HEIGHT))
    el.style.height = `${h}px`
    const scrollable = el.scrollHeight > INPUT_MAX_HEIGHT
    el.style.overflowY = scrollable ? 'auto' : 'hidden'
    el.classList.toggle('chat-input--scrollable', scrollable)
  }

  useEffect(() => {
    adjustInputHeight()
  }, [input])

  const handleSubmit = (e) => {
    e.preventDefault()
    const text = input.trim()
    if (text) {
      onSend(text)
      setInput('')
      if (inputRef.current) {
        inputRef.current.style.height = 'auto'
        inputRef.current.style.overflowY = 'hidden'
      }
    }
  }

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
    }
  }

  const handleBubbleClick = (e) => {
    if (e.target.closest('.chat-send') || e.target.closest('.chat-clear') || e.target === inputRef.current) return
    inputRef.current?.focus()
  }

  const canClear = messages.length > 0
  const handleClearClick = () => {
    if (!canClear) return
    setConfirmClearOpen(true)
  }
  const confirmClear = () => {
    setConfirmClearOpen(false)
    onClearChat?.()
  }

  const renderMessageContent = (m, i) => {
    const isUser = m.sender === 'user'
    const expanded = expandedIndices.has(i)
    const hasOverflow = messageMeta.overflow.has(i)
    const measured = messageMeta.measured.has(i)
    const showExpand = isUser && hasOverflow && !expanded
    const showCollapse = isUser && hasOverflow && expanded
    const needCollapsed = isUser && !expanded && (hasOverflow || !measured)
    const isMarkdown = m.sender === 'assistant' || m.sender === 'auto'
    const isLoading = m.effect?.type === 'loading'

    if (isUser) {
      return (
        <>
          <div className="chat-message-text chat-message-bubble">
            <div
              ref={(el) => { contentRefs.current[i] = el }}
              className={`chat-message-text-inner ${needCollapsed ? 'collapsed' : ''} ${needCollapsed && hasOverflow ? 'has-overflow' : ''}`}
            >
              <SimpleMessageContent text={m.text} />
            </div>
          </div>
          {(showExpand || showCollapse) && (
            <div className="chat-message-expand-actions">
              {showExpand && (
                <button type="button" className="chat-message-expand-toggle" onClick={() => toggleExpanded(i)}>
                  Показать больше
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M6 9l6 6 6-6" />
                  </svg>
                </button>
              )}
              {showCollapse && (
                <button type="button" className="chat-message-expand-toggle" onClick={() => toggleExpanded(i)}>
                  Показать меньше
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M18 15l-6-6-6 6" />
                  </svg>
                </button>
              )}
            </div>
          )}
        </>
      )
    }

    if (isMarkdown) {
      return (
        <>
          <div className="chat-message-content chat-message-content--markdown">
            <MarkdownMessageContent text={m.text} className="chat-message-markdown" />
          </div>
          <MessageActions text={m.text} meta={m.meta} />
        </>
      )
    }

    if (isLoading) {
      return (
        <div className="chat-message-content chat-message-content--simple chat-message-content--loading">
          <span className="chat-loading-text">{m.text || 'Идёт обработка…'}</span>
        </div>
      )
    }

    const isSystem = m.sender === 'system'
    return (
      <div className={`chat-message-content chat-message-content--simple${isSystem ? ' chat-message-content--system' : ''}`}>
        <SimpleMessageContent text={m.text} className="chat-message-simple-text" />
      </div>
    )
  }

  const handleScrollToBottom = () => {
    const el = scrollContainerRef.current
    if (el) {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' })
      userScrolledUpRef.current = false
      showScrollToBottomRef.current = false
      setShowScrollToBottom(false)
    }
  }

  const scrollToBottomButton = (
    <div
      className={`chat-scroll-to-bottom-wrap ${showScrollToBottom ? 'chat-scroll-to-bottom-wrap--visible' : ''}`}
      aria-hidden
    >
      <Tooltip text="Вниз к последнему сообщению">
        <button
          type="button"
          className="chat-scroll-to-bottom-btn"
          onClick={handleScrollToBottom}
          aria-label="Прокрутить вниз"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="chat-scroll-to-bottom-btn__icon">
            <path d="m19 12-7 7-7-7" />
            <path d="M12 5v14" />
          </svg>
        </button>
      </Tooltip>
    </div>
  )

  const chatFooter = (
    <div className="chat-input-wrapper">
      {scrollToBottomButton}
      <div className="chat-input-center">
        <form className="chat-input-row" onSubmit={handleSubmit} onClick={handleBubbleClick}>
          <textarea
            ref={inputRef}
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Введите сообщение..."
            rows={1}
            aria-label="Введите сообщение"
          />
          <div className="chat-input-actions">
            <Tooltip text="Очистить чат">
              <button
                type="button"
                className="chat-clear"
                disabled={!canClear}
                aria-label="Очистить чат"
                onClick={handleClearClick}
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M21 21H8a2 2 0 0 1-1.42-.587l-3.994-3.999a2 2 0 0 1 0-2.828l10-10a2 2 0 0 1 2.829 0l5.999 6a2 2 0 0 1 0 2.828L12.834 21" />
                  <path d="m5.082 11.09 8.828 8.828" />
                </svg>
              </button>
            </Tooltip>
            <Tooltip text="Отправить">
              <button
                type="submit"
                className="chat-send"
                disabled={!input.trim()}
                aria-label="Отправить"
              >
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                  <path d="m5 12 7-7 7 7" />
                  <path d="M12 19V5" />
                </svg>
              </button>
            </Tooltip>
          </div>
        </form>
      </div>
    </div>
  )

  // У чата нет липкого заголовка — убираем верхний отступ, чтобы сообщения при скролле вверх были у начала страницы.
  const chatLayout = { topPadding: 0 }

  return (
    <WorkspaceLayout ref={scrollContainerRef} layout={chatLayout} footer={chatFooter}>
      <div ref={messagesContainerRef} className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-welcome">
            {isLoading ? 'Загрузка...' : 'Добро пожаловать в Coreness Flow!'}
          </div>
        )}
        {messages.map((m, i) => {
          const isRemoving = removingMessageIndices.has(m.message_index)
          const isMessageLoading = m.effect?.type === 'loading'
          return (
            <div
              key={m.message_index ?? i}
              className={`chat-message chat-message--${m.sender}${isMessageLoading ? ' chat-message--loading' : ''}${isRemoving ? ' chat-message--removing' : ''}`}
            >
              {renderMessageContent(m, i)}
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
      <Modal open={confirmClearOpen} onClose={() => setConfirmClearOpen(false)} title="Очистить чат?">
        <p>Все сообщения будут удалены. Продолжить?</p>
        <div className="modal-actions">
          <button type="button" onClick={() => setConfirmClearOpen(false)}>
            Отмена
          </button>
          <button type="button" className="modal-action--danger" onClick={confirmClear}>
            Очистить
          </button>
        </div>
      </Modal>
    </WorkspaceLayout>
  )
}
