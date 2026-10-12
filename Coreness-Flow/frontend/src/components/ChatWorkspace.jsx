/**
 * Воркспейс чата: один инстанс на вкладку, подключает useChatWorkspace(chatId) и рендерит ChatView.
 */

import { useChatWorkspace } from '../hooks/useChatWorkspace'
import ChatView from './ChatView'

export default function ChatWorkspace({ chatId, isActive }) {
  const {
    messages,
    loading,
    removingMessageIndices,
    handleSendMessage,
    handleClearChat,
    handleMessageDrawComplete,
  } = useChatWorkspace(chatId)

  return (
    <ChatView
      messages={messages}
      removingMessageIndices={removingMessageIndices}
      onSend={handleSendMessage}
      onClearChat={handleClearChat}
      isLoading={loading}
      onMessageDrawComplete={handleMessageDrawComplete}
    />
  )
}
