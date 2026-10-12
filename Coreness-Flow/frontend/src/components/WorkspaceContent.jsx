/**
 * Контент воркспейса по роли (kind). Один инстанс на вкладку, lifecycle общий (панель в App).
 */

import ChatWorkspace from './ChatWorkspace'
import SettingsView from './SettingsView'
import ChatListView from './ChatListView'
import PluginWorkspaceView from './PluginWorkspaceView'
import AISettingsView from './AISettingsView'
import { WorkspaceLayout } from '../contributions/workspace'

export default function WorkspaceContent({
  workspace,
  isActive,
  refreshTrigger,
  onCloseWorkspace,
  onSelectChatFromList,
  onDeleteChat,
  onRenameChat,
  openChatIds,
  contributions,
}) {
  const { kind } = workspace

  if (kind === 'chat') {
    return <ChatWorkspace chatId={workspace.id} isActive={isActive} />
  }

  if (kind === 'settings') {
    return (
      <WorkspaceLayout layout={{ topPadding: 'var(--header-row-offset-top)' }}>
        <SettingsView contributions={contributions} onClose={onCloseWorkspace} />
      </WorkspaceLayout>
    )
  }

  if (kind === 'chat_list') {
    return (
      <WorkspaceLayout layout={{ topPadding: 'var(--header-row-offset-top)' }}>
        <ChatListView
          isActive={isActive}
          refreshTrigger={refreshTrigger}
          onSelectChat={onSelectChatFromList}
          onClosePanel={onCloseWorkspace}
          onDeleteChat={onDeleteChat}
          onRenameChat={onRenameChat}
          openChatIds={openChatIds}
        />
      </WorkspaceLayout>
    )
  }

  if (kind === 'ai') {
    return (
      <WorkspaceLayout layout={{ topPadding: 'var(--header-row-offset-top)' }}>
        <AISettingsView onClose={onCloseWorkspace} />
      </WorkspaceLayout>
    )
  }

  if (kind === 'plugin') {
    return (
      <WorkspaceLayout layout={workspace.layout ?? { topPadding: 'var(--header-row-offset-top)' }}>
        <PluginWorkspaceView workspace={workspace} isActive={isActive} refreshTrigger={refreshTrigger} onClose={onCloseWorkspace} />
      </WorkspaceLayout>
    )
  }

  return null
}
