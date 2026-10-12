/**
 * Протокол (шина) фронт–backend: имена действий и событий, фасад для чата.
 * Убирает хардкод строк по компонентам; контракт в одном месте.
 */

import { call, on } from './api'

// --- Действия (request–response) ---
export const ACTION = {
  CHAT_SUBMIT_MESSAGE: 'chat_submit_message',
  CHAT_LIST: 'chat_list',
  CHAT_CREATE: 'chat_create',
  CHAT_GET_MESSAGES: 'chat_get_messages',
  CHAT_GET_MESSAGE: 'chat_get_message',
  CHAT_CLAIM_MESSAGE: 'chat_claim_message',
  CHAT_MARK_MESSAGE_DRAWN: 'chat_mark_message_drawn',
  CHAT_SET_TITLE: 'chat_set_title',
  CHAT_DELETE: 'chat_delete',
  CHAT_SET_PINNED: 'chat_set_pinned',
  CHAT_CLEAR: 'clear_chat',
  REMOVE_CHAT_MESSAGE: 'remove_chat_message',
  CHANGE_CHAT_MESSAGE: 'change_chat_message',
  GET_APP_METADATA: 'get_app_metadata',
  GET_CONTRIBUTIONS: 'get_contributions',
  GET_PLUGIN_SETTINGS: 'get_plugin_settings',
  SET_PLUGIN_SETTINGS: 'set_plugin_settings',
}

// --- События (fire-and-forget с backend) ---
export const EVENT = {
  CHAT_NEW_MESSAGE: 'chat:new_message',
  CHAT_CLEAR: 'chat:clear',
  CHAT_MESSAGE_REMOVED: 'chat:message_removed',
  CHAT_MESSAGE_CHANGED: 'chat:message_changed',
  UI_SHOW_MODAL: 'ui:show_modal',
  VECTOR_STORE_CHUNKS_CHANGED: 'vector_store:chunks_changed',
}

// --- Фасад: чат ---

/** Отправить сообщение пользователя: плагин чата сохраняет в storage и передаёт событие в сценарии. */
export function sendChatMessage(text, chatId = 0) {
  return call(ACTION.CHAT_SUBMIT_MESSAGE, {
    event_type: 'message',
    event_text: text,
    event_source: 'app',
    app_chat_id: Number(chatId),
    event_timestamp: Math.floor(Date.now() / 1000),
  })
}

/** Список чатов (id, title, created_at), новые сверху. */
export function chatList() {
  return call(ACTION.CHAT_LIST, {})
}

/** Создать чат. Возврат: { id, title, created_at }. */
export function chatCreate(title) {
  return call(ACTION.CHAT_CREATE, title != null ? { title } : {})
}

/** Все сообщения чата (при открытии вкладки). */
export function chatGetMessages(chatId) {
  return call(ACTION.CHAT_GET_MESSAGES, { app_chat_id: Number(chatId) })
}

/** Одно сообщение по индексу (по событию — запрос конкретного сообщения). */
export function chatGetMessage(chatId, messageIndex) {
  return call(ACTION.CHAT_GET_MESSAGE, { app_chat_id: Number(chatId), message_index: Number(messageIndex) })
}

/** Пометить сообщение как не новое и вернуть данные (один источник правды для отображения по событию). */
export function chatClaimMessage(chatId, messageIndex) {
  return call(ACTION.CHAT_CLAIM_MESSAGE, { app_chat_id: Number(chatId), message_index: Number(messageIndex) })
}

/** Пометить сообщение как отрисованное (is_new=false). Вызывать перед анимацией. */
export function chatMarkMessageDrawn(chatId, messageIndex) {
  return call(ACTION.CHAT_MARK_MESSAGE_DRAWN, { app_chat_id: Number(chatId), message_index: Number(messageIndex) })
}

/** Переименовать чат. */
export function chatSetTitle(chatId, title) {
  return call(ACTION.CHAT_SET_TITLE, { app_chat_id: Number(chatId), title })
}

/** Удалить чат (только пользовательские, id >= 10). */
export function chatDelete(chatId) {
  return call(ACTION.CHAT_DELETE, { app_chat_id: Number(chatId) })
}

/** Закрепить или открепить чат (только пользовательские, id >= 10). */
export function chatSetPinned(chatId, pinned) {
  return call(ACTION.CHAT_SET_PINNED, { app_chat_id: Number(chatId), pinned: Boolean(pinned) })
}

/** Очистить историю сообщений чата (storage + UI). */
export function clearChat(chatId) {
  return call(ACTION.CHAT_CLEAR, { app_chat_id: Number(chatId) })
}

/** Удалить одно сообщение из чата (storage + UI). */
export function removeChatMessage(chatId, messageIndex) {
  return call(ACTION.REMOVE_CHAT_MESSAGE, { app_chat_id: Number(chatId), message_index: Number(messageIndex) })
}

/** Изменить сообщение по индексу (текст, sender, meta, effect). UI получит chat:message_changed. */
export function changeChatMessage(chatId, messageIndex, opts = {}) {
  const payload = { app_chat_id: Number(chatId), message_index: Number(messageIndex) }
  if (opts.text != null) payload.text = opts.text
  if (opts.sender != null) payload.sender = opts.sender
  if (opts.meta != null) payload.meta = opts.meta
  if ('effect' in opts) payload.effect = opts.effect
  if (opts.transition_effect != null) payload.transition_effect = opts.transition_effect
  return call(ACTION.CHANGE_CHAT_MESSAGE, payload)
}

/** Подписаться на новые сообщения. data: { app_chat_id?, last_message_index }. */
export function onChatMessage(callback) {
  return on(EVENT.CHAT_NEW_MESSAGE, callback)
}

/** Подписаться на очистку чата. data: { app_chat_id? }. */
export function onChatClear(callback) {
  return on(EVENT.CHAT_CLEAR, callback)
}

/** Подписаться на удаление одного сообщения. data: { app_chat_id, message_index }. */
export function onChatMessageRemoved(callback) {
  return on(EVENT.CHAT_MESSAGE_REMOVED, callback)
}

/** Подписаться на изменение сообщения. data: { app_chat_id, message_index, message, transition_effect? }. */
export function onChatMessageChanged(callback) {
  return on(EVENT.CHAT_MESSAGE_CHANGED, callback)
}

/** Метаданные приложения (paths, about для блока «О приложении»). */
export function getAppMetadata() {
  return call(ACTION.GET_APP_METADATA, {})
}

/** Все контрибьюты плагинов (config.contributes): workspace, sidebar, menus и т.д. */
export function getContributions() {
  return call(ACTION.GET_CONTRIBUTIONS, {})
}

/** Схема и текущие значения настроек плагина для формы (response_data: schema, values). */
export function getPluginSettings(pluginId) {
  return call(ACTION.GET_PLUGIN_SETTINGS, { plugin_id: pluginId })
}

/** Сохранить переопределения настроек плагина; бэкенд эмитит plugin:settings_changed:{pluginId} (только для этого плагина). */
export function setPluginSettings(pluginId, settings) {
  return call(ACTION.SET_PLUGIN_SETTINGS, { plugin_id: pluginId, settings })
}

/** Вызов действия по имени (для пунктов sidebar/menus из контрибьюта). */
export function callAction(actionName, payload = {}) {
  return call(actionName, payload)
}

/** Подписаться на показ модалки по событию с бэкенда (data: title, body?, buttons?). */
export function onShowModal(callback) {
  return on(EVENT.UI_SHOW_MODAL, callback)
}

/** Подписаться на изменение чанков в векторной базе (add_chunks/delete_chunks). Для обновления вкладки «Векторная база». */
export function onVectorStoreChunksChanged(callback) {
  return on(EVENT.VECTOR_STORE_CHUNKS_CHANGED, callback)
}
