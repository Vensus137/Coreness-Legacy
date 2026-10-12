/**
 * Список чатов: закреплённые и остальные, название, дата, выбор, пин/анпин (только пользовательские), переименование, удаление.
 * Данные через chat_list (pinned приходит с бэка). Системные чаты всегда закреплены, пин/удаление для них не показываются.
 */

import { useState, useEffect, useRef } from 'react'
import { chatList, chatDelete, chatSetTitle, chatSetPinned } from '../protocol'
import Modal from './Modal'
import { IconPin, IconPinOff, IconTrash2, IconPencil } from './Icons'
import Tooltip from './Tooltip'

const SYSTEM_CHAT_ID_THRESHOLD = 10

/** Прошедшее время: "1m", "2h", "1d", "34d" (минуты, часы, дни). */
function formatRelativeTime(iso) {
  if (!iso) return ''
  try {
    const diff = Date.now() - new Date(iso).getTime()
    const min = Math.floor(diff / 60000)
    const h = Math.floor(diff / 3600000)
    const d = Math.floor(diff / 86400000)
    if (d > 0) return `${d}d`
    if (h > 0) return `${h}h`
    if (min > 0) return `${min}m`
    return '0m'
  } catch {
    return ''
  }
}

/** Бэкенд возвращает чаты уже отсортированными (сначала закреплённые, по дате). Разбиваем на два списка для отображения. */
function splitPinnedUnpinned(chats) {
  const pinned = (chats || []).filter((c) => c.pinned === true)
  const unpinned = (chats || []).filter((c) => !c.pinned)
  return { pinned, unpinned }
}

/** Проверка, что список чатов не изменился (id, порядок, title, pinned) — чтобы не делать лишний ре-рендер. */
function chatsEqual(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false
  return a.every((c, i) => {
    const d = b[i]
    return d && c.id === d.id && (c.title || '') === (d.title || '') && !!c.pinned === !!d.pinned
  })
}

export default function ChatListView({ isActive, refreshTrigger, onSelectChat, onClosePanel, onDeleteChat, onRenameChat, openChatIds = [] }) {
  const [chats, setChats] = useState([])
  const [confirmDeleteId, setConfirmDeleteId] = useState(null)
  const [editingChatId, setEditingChatId] = useState(null)
  const [editingTitle, setEditingTitle] = useState('')
  const renameInputRef = useRef(null)
  const listRef = useRef(null)

  useEffect(() => {
    if (editingChatId == null) return
    const t = requestAnimationFrame(() => {
      renameInputRef.current?.focus()
      renameInputRef.current?.select()
    })
    return () => cancelAnimationFrame(t)
  }, [editingChatId])

  /** Тихий апдейт: запрос в фоне, без блокировки UI; state обновляем только если данные изменились. */
  const loadList = () => {
    chatList()
      .then((res) => {
        const next = res?.result === 'success' && Array.isArray(res?.response_data?.chats) ? res.response_data.chats : []
        setChats((prev) => (chatsEqual(prev, next) ? prev : next))
      })
      .catch(() => setChats((prev) => (chatsEqual(prev, []) ? prev : [])))
  }

  useEffect(() => {
    if (isActive && refreshTrigger != null) loadList()
  }, [isActive, refreshTrigger])

  const handleSelect = (chat) => {
    onSelectChat(chat)
  }

  const handleDeleteClick = (e, chatId) => {
    e.stopPropagation()
    if (chatId < 10) return
    setConfirmDeleteId(chatId)
  }

  const confirmDelete = () => {
    if (confirmDeleteId == null) return
    const id = confirmDeleteId
    setConfirmDeleteId(null)
    chatDelete(id)
      .then(() => {
        setChats((prev) => prev.filter((c) => c.id !== id))
        onDeleteChat?.(id)
      })
      .catch(() => setConfirmDeleteId(null))
  }

  const startRename = (e, chat) => {
    e.stopPropagation()
    setEditingChatId(chat.id)
    setEditingTitle(chat.title || `Чат ${chat.id}`)
  }

  const saveRename = () => {
    if (editingChatId == null) return
    const id = editingChatId
    const title = editingTitle?.trim() || (chats.find((c) => c.id === id)?.title || `Чат ${id}`)
    const prevTitle = editingTitle
    setEditingChatId(null)
    setEditingTitle('')
    chatSetTitle(id, title)
      .then((res) => {
        if (res?.result === 'success') {
          setChats((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)))
          onRenameChat?.(id, title)
        } else {
          setEditingChatId(id)
          setEditingTitle(prevTitle)
        }
      })
      .catch(() => {
        setEditingChatId(id)
        setEditingTitle(prevTitle)
      })
  }

  const cancelRename = () => {
    setEditingChatId(null)
    setEditingTitle('')
  }

  const handlePinClick = (e, chat) => {
    e.stopPropagation()
    if (chat.id < SYSTEM_CHAT_ID_THRESHOLD) return
    const nextPinned = !chat.pinned
    chatSetPinned(chat.id, nextPinned)
      .then((res) => {
        if (res?.result === 'success') {
          setChats((prev) => prev.map((c) => (c.id === chat.id ? { ...c, pinned: nextPinned } : c)))
        }
      })
      .catch(() => {})
  }

  const { pinned: pinnedChats, unpinned: unpinnedChats } = splitPinnedUnpinned(chats)

  const renderChatItem = (chat) => {
    const isEditing = editingChatId === chat.id
    const isUserChat = chat.id >= SYSTEM_CHAT_ID_THRESHOLD
    const dateActions = (
      <span className="chat-list-view-item-date-actions">
        <span className="chat-list-view-item-date">{formatRelativeTime(chat.created_at)}</span>
        <div className="chat-list-view-item-actions">
          {isUserChat && (
            <Tooltip text={chat.pinned ? 'Открепить' : 'Закрепить'}>
              <button
                type="button"
                className="chat-list-view-item-action icon-btn-muted"
                onClick={(e) => handlePinClick(e, chat)}
                aria-label={chat.pinned ? 'Открепить' : 'Закрепить'}
              >
                {chat.pinned ? <IconPinOff /> : <IconPin />}
              </button>
            </Tooltip>
          )}
          <Tooltip text="Переименовать">
            <button
              type="button"
              className="chat-list-view-item-action icon-btn-muted"
              onClick={(e) => startRename(e, chat)}
              aria-label="Переименовать"
            >
              <IconPencil />
            </button>
          </Tooltip>
          {isUserChat ? (
            <Tooltip text="Удалить">
              <button
                type="button"
                className="chat-list-view-item-action icon-btn-muted"
                onClick={(e) => handleDeleteClick(e, chat.id)}
                aria-label="Удалить"
              >
                <IconTrash2 />
              </button>
            </Tooltip>
          ) : null}
        </div>
      </span>
    )
    return (
      <li key={chat.id} className={`chat-list-view-item ${isEditing ? 'chat-list-view-item--editing' : ''}`}>
        {isEditing ? (
          <div className="chat-list-view-item-main chat-list-view-item-main--edit">
            <input
              ref={renameInputRef}
              type="text"
              className="chat-list-view-item-title-input"
              value={editingTitle}
              onChange={(e) => setEditingTitle(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') {
                  e.preventDefault()
                  saveRename()
                } else if (e.key === 'Escape') {
                  e.preventDefault()
                  cancelRename()
                }
              }}
              onBlur={saveRename}
              onClick={(e) => e.stopPropagation()}
              aria-label="Название чата"
            />
            {dateActions}
          </div>
        ) : (
          <button
            type="button"
            className="chat-list-view-item-main"
            onClick={() => handleSelect(chat)}
          >
            <span className="chat-list-view-item-title">{chat.title || `Чат ${chat.id}`}</span>
            {dateActions}
          </button>
        )}
      </li>
    )
  }

  return (
    <div className="chat-list-view">
      <div className="chat-list-view-header workspace-sticky-header">
        <h2 className="chat-list-view-title">Чаты</h2>
        <Tooltip text="Закрыть">
          <button type="button" className="chat-list-view-back" onClick={onClosePanel}>
            Закрыть
          </button>
        </Tooltip>
      </div>
      {/* Тихий апдейт: контент не подменяется «Загрузка…», запрос идёт в фоне, после ответа — обновление только при изменении данных. */}
      <div ref={listRef} className="chat-list-view-body">
        {pinnedChats.length > 0 && (
          <>
            <div className="chat-list-view-section">
              <h3 className="chat-list-view-section-title">Закреплённые</h3>
            </div>
            <ul className="chat-list-view-list" role="list">
              {pinnedChats.map(renderChatItem)}
            </ul>
          </>
        )}
        {unpinnedChats.length > 0 && (
          <>
            <div className="chat-list-view-section">
              <h3 className="chat-list-view-section-title">Остальные</h3>
            </div>
            <ul className="chat-list-view-list" role="list">
              {unpinnedChats.map(renderChatItem)}
            </ul>
          </>
        )}
        {pinnedChats.length === 0 && unpinnedChats.length === 0 && (
          <div className="chat-list-view-loading">Нет чатов</div>
        )}
      </div>
      <Modal
        open={confirmDeleteId != null}
        onClose={() => setConfirmDeleteId(null)}
        title="Удалить чат?"
      >
        <p>Чат будет удалён без возможности восстановления.</p>
        <div className="modal-actions">
          <button type="button" onClick={() => setConfirmDeleteId(null)}>
            Отмена
          </button>
          <button type="button" className="modal-action--danger" onClick={confirmDelete}>
            Удалить
          </button>
        </div>
      </Modal>
    </div>
  )
}
