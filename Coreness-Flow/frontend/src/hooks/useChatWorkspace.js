/**
 * Логика воркспейса одного чата. Один инстанс на вкладку чата; кэш и очередь не сбрасываются при переключении вкладок.
 * Мерж по message_index.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import {
  sendChatMessage,
  clearChat,
  onChatMessage,
  onChatClear,
  onChatMessageRemoved,
  onChatMessageChanged,
  chatGetMessages,
  chatClaimMessage,
} from '../protocol'

/** Добавить или обновить сообщение в списке по message_index; вернуть новый массив без дублей. */
function mergeMessageIntoList(list, message) {
  const idx = message.message_index
  if (idx == null && idx !== 0) return [...list, message]
  const i = list.findIndex((m) => (m.message_index ?? null) === idx)
  if (i >= 0) {
    const next = [...list]
    next[i] = { ...next[i], ...message }
    return next
  }
  const next = [...list, message]
  next.sort((a, b) => (a.message_index ?? -1) - (b.message_index ?? -1))
  return next
}

/** Объединить список с сервера с текущим по message_index (при load). */
function mergeMessagesFromServer(current, fromServer) {
  if (!Array.isArray(fromServer) || fromServer.length === 0) return current || []
  let result = current || []
  for (const m of fromServer) {
    result = mergeMessageIntoList(result, { ...m, _new: !!m.is_new })
  }
  return result
}

const REMOVAL_ANIMATION_MS = 280

export function useChatWorkspace(chatId) {
  const [messages, setMessages] = useState([])
  const [loading, setLoading] = useState(false)
  const [removingMessageIndices, setRemovingMessageIndices] = useState(() => new Set())

  const queueRef = useRef([])
  const processingRef = useRef(false)
  const removalTimeoutsRef = useRef({})

  const loadMessages = useCallback((cid, onLoaded) => {
    setLoading(true)
    chatGetMessages(cid)
      .then((res) => {
        if (res?.result === 'success' && Array.isArray(res?.response_data?.messages)) {
          const fromServer = res.response_data.messages.map((m) => ({ ...m, _new: !!m.is_new }))
          setMessages((prev) => mergeMessagesFromServer(prev, fromServer))
        } else {
          setMessages([])
        }
      })
      .catch(() => setMessages([]))
      .finally(() => {
        setLoading(false)
        if (typeof onLoaded === 'function') onLoaded(cid)
      })
  }, [])

  const processQueue = useCallback(() => {
    if (processingRef.current || queueRef.current.length === 0) return
    processingRef.current = true
    const item = queueRef.current.shift()
    const itemCid = item.app_chat_id
    chatClaimMessage(itemCid, item.last_message_index)
      .then((res) => {
        if (res?.result !== 'success' || !res?.response_data?.message) {
          processingRef.current = false
          if (queueRef.current.length > 0) processQueue()
          return
        }
        const m = { ...res.response_data.message, _new: true }
        setMessages((prev) => {
          const withoutOptimistic = prev.filter((msg) => !msg._optimistic)
          const base = prev.length !== withoutOptimistic.length ? withoutOptimistic : prev
          return mergeMessageIntoList(base, m)
        })
        processingRef.current = false
        if (queueRef.current.length > 0) processQueue()
      })
      .catch(() => {
        processingRef.current = false
        if (queueRef.current.length > 0) processQueue()
      })
  }, [])

  // Загрузка при монтировании
  useEffect(() => {
    loadMessages(chatId, processQueue)
  }, [chatId, loadMessages, processQueue])

  // Подписки: только события этого чата
  useEffect(() => {
    const unsubMessage = onChatMessage((data) => {
      const cid = Number(data.app_chat_id)
      if (cid !== chatId) return
      const idx = data.last_message_index
      if (idx == null || idx < 0) return
      queueRef.current.push({ app_chat_id: cid, last_message_index: idx })
      processQueue()
    })
    const unsubClear = onChatClear((data) => {
      const cid = Number(data.app_chat_id)
      if (cid !== chatId) return
      setMessages([])
      queueRef.current = []
    })
    const unsubRemoved = onChatMessageRemoved((data) => {
      const cid = Number(data.app_chat_id)
      if (cid !== chatId) return
      const idx = typeof data.message_index === 'number' ? data.message_index : Number(data.message_index)
      if (Number.isNaN(idx)) return
      setRemovingMessageIndices((prev) => new Set(prev).add(idx))
      if (removalTimeoutsRef.current[idx]) return
      removalTimeoutsRef.current[idx] = setTimeout(() => {
        delete removalTimeoutsRef.current[idx]
        setMessages((prev) => prev.filter((m) => (m.message_index ?? null) !== idx))
        setRemovingMessageIndices((prev) => {
          const next = new Set(prev)
          next.delete(idx)
          return next
        })
      }, REMOVAL_ANIMATION_MS)
    })
    const unsubChanged = onChatMessageChanged((data) => {
      const cid = Number(data.app_chat_id)
      if (cid !== chatId) return
      const msg = data.message
      if (!msg || (msg.message_index ?? null) == null) return
      setMessages((prev) => mergeMessageIntoList(prev, { ...msg, _new: false }))
    })
    return () => {
      unsubMessage()
      unsubClear()
      unsubRemoved()
      unsubChanged()
      Object.values(removalTimeoutsRef.current).forEach(clearTimeout)
      removalTimeoutsRef.current = {}
    }
  }, [chatId, processQueue])

  const handleSendMessage = useCallback(
    (text) => {
      setMessages((prev) => [...prev, { text, sender: 'user', _optimistic: true }])
      sendChatMessage(text, chatId)
        .then((result) => {
          if (result?.result === 'error') {
            const msg = result?.error?.message ?? 'Ошибка'
            setMessages((prev) => [...prev, { text: `Ошибка: ${msg}`, sender: 'error' }])
          }
        })
        .catch((err) => {
          setMessages((prev) => [...prev, { text: `Ошибка: ${err.message}`, sender: 'error' }])
        })
    },
    [chatId]
  )

  const handleMessageDrawComplete = useCallback(() => {
    processQueue()
  }, [processQueue])

  const handleClearChat = useCallback(() => {
    if (messages.length === 0) return
    clearChat(chatId)
  }, [chatId, messages.length])

  return {
    messages,
    loading,
    removingMessageIndices,
    handleSendMessage,
    handleClearChat,
    handleMessageDrawComplete,
  }
}
