/**
 * Сайдбар: сверху — иконки (Настройки, История чатов, Справка), ниже — список пунктов.
 * Настройки — воркспейс настроек, История — список чатов, Справка — модальное окно «О приложении».
 */

import { IconSettings, IconAI, IconHistory } from './Icons'
import Tooltip from './Tooltip'

export default function Sidebar({
  sidebarItems = [],
  onSidebarItemClick,
  onOpenChatList,
  onOpenSettings,
  onOpenAI,
  activeSection = null,
}) {
  const getSidebarItemKey = (item) => {
    if (item.type === 'workspace') return `ws_${item.pluginId}_${item.id}`
    return `sb_${item.pluginId}_${item.id}`
  }

  const isSidebarItemActive = (item) => {
    if (item.type === 'workspace') return activeSection === `plugin_${item.pluginId}`
    return false
  }

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <Tooltip text="Настройки">
          <button
            type="button"
            className={`sidebar-item sidebar-item-icon ${activeSection === 'settings' ? 'sidebar-item--active' : ''}`}
            onClick={onOpenSettings}
            aria-label="Настройки"
          >
            <IconSettings />
          </button>
        </Tooltip>
        <Tooltip text="AI">
          <button
            type="button"
            className={`sidebar-item sidebar-item-icon ${activeSection === 'ai' ? 'sidebar-item--active' : ''}`}
            onClick={onOpenAI}
            aria-label="AI"
          >
            <IconAI />
          </button>
        </Tooltip>
        <Tooltip text="История чатов">
          <button
            type="button"
            className={`sidebar-item sidebar-item-icon ${activeSection === 'chat_list' ? 'sidebar-item--active' : ''}`}
            onClick={onOpenChatList}
            aria-label="История чатов"
          >
            <IconHistory />
          </button>
        </Tooltip>
      </div>
      <div className="sidebar-content">
        {sidebarItems.map((item) => (
          <button
            key={getSidebarItemKey(item)}
            type="button"
            className={`sidebar-item ${isSidebarItemActive(item) ? 'sidebar-item--active' : ''}`}
            onClick={() => onSidebarItemClick?.(item)}
          >
            {item.label}
          </button>
        ))}
      </div>
    </aside>
  )
}
