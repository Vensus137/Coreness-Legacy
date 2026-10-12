import { useState, useEffect, useMemo, useRef } from 'react'
import { chatCreate, chatSetTitle, chatList, getAppMetadata, getContributions, callAction, onShowModal, onChatMessage, onVectorStoreChunksChanged } from './protocol'
import { getSidebarItems } from './contributions/sidebar'
import { getTabContextMenuExtraItems } from './contributions/menus'
import TitleBar from './components/TitleBar'
import Sidebar from './components/Sidebar'
import TabBar from './components/TabBar'
import WorkspaceContent from './components/WorkspaceContent'
import Modal from './components/Modal'
import AboutContent, { buildAboutCopyText } from './components/AboutContent'
import './styles/layout.css'
import './styles/icon-btn-muted.css'
import './styles/title-bar.css'
import './styles/dropdown.css'
import './styles/sidebar.css'
import './styles/tab-bar.css'
import './styles/chat.css'
import './styles/chat-messages.css'
import './styles/chat-input.css'
import './styles/chat-list.css'
import './styles/settings.css'
import './styles/modal.css'
import './styles/tooltip.css'
import './styles/workspace.css'

const KIND_CHAT = 'chat'
const KIND_SETTINGS = 'settings'
const KIND_CHAT_LIST = 'chat_list'
const KIND_PLUGIN = 'plugin'
const KIND_AI = 'ai'

const DEFAULT_CHAT = { id: 0, kind: KIND_CHAT, title: 'Основной' }
const CHAT_LIST_WORKSPACE = { id: 'chat_list', kind: KIND_CHAT_LIST, title: 'История чатов', refreshOnActivate: true }

export default function App() {
  const [workspaces, setWorkspaces] = useState([DEFAULT_CHAT])
  const [activeIndex, setActiveIndex] = useState(0)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [aboutOpen, setAboutOpen] = useState(false)
  const [appAbout, setAppAbout] = useState(null)
  const [editingTabIndex, setEditingTabIndex] = useState(null)
  /** Счётчики для воркспейсов с refreshOnActivate: при переключении на вкладку инкремент → контент перезапрашивает данные. */
  const [refreshTriggers, setRefreshTriggers] = useState({})
  /** Все контрибьюты плагинов (config.contributes), запрашиваются при монтировании. */
  const [contributions, setContributions] = useState({ workspace: [], settings: [], sidebar: [], menus: {} })
  /** Модалка по событию ui:show_modal с бэкенда: { title, body?, buttons? }. */
  const [contributionModal, setContributionModal] = useState({ open: false, title: '', body: null, buttons: [] })
  /** id вкладок (workspace.id) с «новым сообщением в фоне» — мигают, пока пользователь не переключится на вкладку. */
  const [tabAttentionIds, setTabAttentionIds] = useState([])

  const current = workspaces[activeIndex]

  const sidebarItems = useMemo(() => getSidebarItems(contributions), [contributions])

  useEffect(() => {
    getContributions()
      .then((res) => {
        if (res?.result === 'success' && res?.response_data?.contributions && typeof res.response_data.contributions === 'object') {
          const c = res.response_data.contributions
          setContributions({
            workspace: c.workspace ?? [],
            settings: c.settings ?? [],
            sidebar: c.sidebar ?? [],
            menus: c.menus ?? {},
          })
        } else {
          setContributions({ workspace: [], settings: [], sidebar: [], menus: {} })
        }
      })
      .catch(() => setContributions({ workspace: [], settings: [], sidebar: [], menus: {} }))
  }, [])

  useEffect(() => {
    const unsub = onShowModal((data) => {
      if (data && typeof data === 'object') {
        setContributionModal({
          open: true,
          title: data.title ?? '',
          body: data.body ?? null,
          buttons: Array.isArray(data.buttons) ? data.buttons : [],
        })
      }
    })
    return unsub
  }, [])

  const workspacesRef = useRef(workspaces)
  workspacesRef.current = workspaces
  const activeIndexRef = useRef(activeIndex)
  activeIndexRef.current = activeIndex
  // При новом сообщении в чате: если вкладка не активна — помечаем её для эффекта «внимание»
  useEffect(() => {
    const unsub = onChatMessage((data) => {
      if (data?.app_chat_id == null) return
      const chatId = Number(data.app_chat_id)
      const ws = workspacesRef.current
      const idx = ws.findIndex((w) => w.kind === KIND_CHAT && w.id === chatId)
      if (idx >= 0 && idx !== activeIndexRef.current) {
        const targetId = ws[idx].id
        setTabAttentionIds((prev) => (prev.includes(targetId) ? prev : [...prev, targetId]))
      }
    })
    return unsub
  }, [])

  useEffect(() => {
    const unsub = onVectorStoreChunksChanged(() => {
      const ws = workspacesRef.current
      const v = ws.find((w) => w.kind === KIND_PLUGIN && w.pluginId === 'vector_store' && w.contributionId === 'vector_store_admin')
      if (v?.id) setRefreshTriggers((prev) => ({ ...prev, [v.id]: (prev[v.id] ?? 0) + 1 }))
    })
    return unsub
  }, [])

  useEffect(() => {
    const ws = workspaces[activeIndex]
    if (ws?.refreshOnActivate) {
      setRefreshTriggers((prev) => ({ ...prev, [ws.id]: (prev[ws.id] ?? 0) + 1 }))
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps -- инкремент только при смене вкладки, не при изменении списка воркспейсов
  }, [activeIndex])


  // При открытии «О приложении» подгрузить метаданные (about) с бэка
  useEffect(() => {
    if (!aboutOpen) return
    getAppMetadata()
      .then((res) => {
        if (res?.result === 'success' && Array.isArray(res?.response_data?.about)) {
          setAppAbout(res.response_data.about)
        } else {
          setAppAbout([])
        }
      })
      .catch(() => setAppAbout([]))
  }, [aboutOpen])

  // При старте подтянуть реальное название основного чата (id 0) из бэка, чтобы переименование сохранялось после перезапуска
  useEffect(() => {
    chatList()
      .then((res) => {
        if (res?.result !== 'success' || !Array.isArray(res?.response_data?.chats)) return
        const chat0 = res.response_data.chats.find((c) => c.id === 0)
        if (chat0 == null) return
        setWorkspaces((prev) => {
          const first = prev[0]
          if (first?.kind !== KIND_CHAT || first?.id !== 0) return prev
          return [{ ...first, title: chat0.title || 'Основной' }, ...prev.slice(1)]
        })
      })
      .catch(() => {})
  }, [])

  const addChat = () => {
    chatCreate()
      .then((res) => {
        if (res?.result !== 'success' || res?.response_data == null) return
        const { id, title } = res.response_data
        setWorkspaces((prev) => [...prev, { id, kind: KIND_CHAT, title }])
        setActiveIndex(workspaces.length)
      })
      .catch(() => {})
  }

  const closeWorkspace = (index) => {
    const closedId = workspaces[index]?.id
    setWorkspaces((prev) => {
      if (prev.length <= 1) return prev
      return prev.filter((_, i) => i !== index)
    })
    if (closedId != null) setTabAttentionIds((prev) => prev.filter((id) => id !== closedId))
    setActiveIndex((idx) => (idx === index ? Math.max(0, index - 1) : idx > index ? idx - 1 : idx))
    setEditingTabIndex((current) => (current === index ? null : current > index ? current - 1 : current))
  }

  const openChatList = () => {
    const idx = workspaces.findIndex((w) => w.kind === KIND_CHAT_LIST)
    if (idx >= 0) {
      setActiveIndex(idx)
      return
    }
    setWorkspaces((prev) => [...prev, CHAT_LIST_WORKSPACE])
    setActiveIndex(workspaces.length)
  }

  const handleSelectChatFromList = (chat) => {
    const idx = workspaces.findIndex((w) => w.kind === KIND_CHAT && w.id === chat.id)
    if (idx >= 0) {
      setActiveIndex(idx)
    } else {
      const next = [...workspaces, { id: chat.id, kind: KIND_CHAT, title: chat.title || `Чат ${chat.id}` }]
      setWorkspaces(next)
      setActiveIndex(next.length - 1)
    }
  }

  const handleChatListClose = (deletedChatId) => {
    if (deletedChatId != null) {
      const deletedIndex = workspaces.findIndex((w) => w.kind === KIND_CHAT && w.id === deletedChatId)
      setWorkspaces((prev) => {
        const next = prev.filter((w) => w.kind !== KIND_CHAT || w.id !== deletedChatId)
        return next.length ? next : [DEFAULT_CHAT]
      })
      setActiveIndex((i) => {
        if (deletedIndex < 0) return i
        if (i === deletedIndex) return Math.max(0, deletedIndex - 1)
        return i > deletedIndex ? i - 1 : i
      })
    }
  }

  const handleChatRename = (chatId, newTitle) => {
    setWorkspaces((prev) =>
      prev.map((ws) => (ws.kind === KIND_CHAT && ws.id === chatId ? { ...ws, title: newTitle } : ws))
    )
  }

  const handleTabRename = (index, newTitle) => {
    const w = workspaces[index]
    if (w?.kind === KIND_CHAT && newTitle?.trim()) {
      chatSetTitle(w.id, newTitle.trim()).then((res) => {
        if (res?.result === 'success') {
          setWorkspaces((prev) => prev.map((ws, i) => (i === index ? { ...ws, title: newTitle.trim() } : ws)))
        }
        setEditingTabIndex(null)
      })
    } else {
      setEditingTabIndex(null)
    }
  }

  const handleReorderTabs = (fromIndex, toIndex) => {
    if (fromIndex === toIndex || fromIndex < 0 || toIndex < 0 || fromIndex >= workspaces.length || toIndex >= workspaces.length) return
    const item = workspaces[fromIndex]
    const next = workspaces.filter((_, i) => i !== fromIndex)
    next.splice(toIndex, 0, item)
    setWorkspaces(next)
    setActiveIndex(toIndex)
    setEditingTabIndex((prev) => {
      if (prev == null) return null
      if (prev === fromIndex) return toIndex
      if (fromIndex < prev && toIndex >= prev) return prev - 1
      if (fromIndex > prev && toIndex <= prev) return prev + 1
      return prev
    })
  }

  const openSettings = () => {
    const idx = workspaces.findIndex((w) => w.kind === KIND_SETTINGS)
    if (idx >= 0) {
      setActiveIndex(idx)
      return
    }
    setWorkspaces((prev) => [...prev, { id: `settings_${Date.now()}`, kind: KIND_SETTINGS, title: 'Настройки' }])
    setActiveIndex(workspaces.length)
  }

  const openAI = () => {
    const idx = workspaces.findIndex((w) => w.kind === KIND_AI)
    if (idx >= 0) {
      setActiveIndex(idx)
      return
    }
    setWorkspaces((prev) => [...prev, { id: `ai_${Date.now()}`, kind: KIND_AI, title: 'AI' }])
    setActiveIndex(workspaces.length)
  }

  const handleSelectTab = (index) => {
    setActiveIndex(index)
    const id = workspaces[index]?.id
    if (id != null) setTabAttentionIds((prev) => prev.filter((x) => x !== id))
  }

  const openPluginWorkspace = (contribution) => {
    const { id: contributionId, label, title, pluginId, layout, content } = contribution
    const id = `plugin_${pluginId}_${contributionId}`
    const idx = workspaces.findIndex((w) => w.kind === KIND_PLUGIN && w.pluginId === pluginId && w.contributionId === contributionId)
    if (idx >= 0) {
      setActiveIndex(idx)
      return
    }
    setWorkspaces((prev) => [
      ...prev,
      { id, kind: KIND_PLUGIN, title: title ?? label, pluginId, contributionId, layout, content, refreshOnActivate: true },
    ])
    setActiveIndex(workspaces.length)
  }

  const handleSidebarItemClick = (item) => {
    if (item.type === 'builtin' && item.id === 'chat_list') {
      openChatList()
      return
    }
    if (item.type === 'workspace') {
      openPluginWorkspace(item)
      return
    }
    if (item.type === 'sidebar' && item.action) {
      const actionName = item.action?.callAction ?? item.action
      if (actionName) callAction(actionName, item.action?.payload ?? {}).catch(() => {})
    }
  }

  const handleTabContextMenuItemClick = (item, index) => {
    if (item.builtIn && item.id === 'rename') {
      setEditingTabIndex(index)
      return
    }
    if (!item.builtIn && item.action) {
      callAction(item.action, {}).catch(() => {})
    }
  }

  const tabContextMenuItems = [
    { builtIn: true, id: 'rename', label: 'Переименовать' },
    ...getTabContextMenuExtraItems(contributions?.menus ?? {}),
  ]

  return (
    <div className="app">
      <TitleBar
        sidebarOpen={sidebarOpen}
        onSidebarToggle={() => setSidebarOpen((v) => !v)}
        onOpenAbout={() => setAboutOpen(true)}
        tabBar={
          <TabBar
            workspaces={workspaces}
            activeIndex={activeIndex}
            onSelect={handleSelectTab}
            onAdd={addChat}
            tabAttentionIds={tabAttentionIds}
            onClose={closeWorkspace}
            onReorder={handleReorderTabs}
            onTabRename={handleTabRename}
            editingTabIndex={editingTabIndex}
            setEditingTabIndex={setEditingTabIndex}
            tabContextMenuItems={tabContextMenuItems}
            onTabContextMenuItemClick={handleTabContextMenuItemClick}
          />
        }
      />
      <div className="app-body">
        <div className={`sidebar-container ${sidebarOpen ? '' : 'sidebar-container--closed'}`}>
          <Sidebar
            sidebarItems={sidebarItems}
            onSidebarItemClick={handleSidebarItemClick}
            onOpenChatList={openChatList}
            onOpenSettings={openSettings}
            onOpenAI={openAI}
            activeSection={
              current?.kind === KIND_SETTINGS
                ? 'settings'
                : current?.kind === KIND_AI
                  ? 'ai'
                  : current?.kind === KIND_CHAT_LIST
                    ? 'chat_list'
                    : current?.pluginId
                      ? `plugin_${current.pluginId}`
                      : null
            }
          />
        </div>
        <main className="main">
          <div className="content">
            {workspaces.map((ws, i) => (
              <div
                key={ws.id}
                className="workspace-pane"
                style={{ display: activeIndex === i ? 'flex' : 'none' }}
                aria-hidden={activeIndex !== i}
              >
                <WorkspaceContent
                  workspace={ws}
                  isActive={activeIndex === i}
                  refreshTrigger={refreshTriggers[ws.id]}
                  onCloseWorkspace={() => closeWorkspace(i)}
                  onSelectChatFromList={handleSelectChatFromList}
                  onDeleteChat={handleChatListClose}
                  onRenameChat={handleChatRename}
                  openChatIds={workspaces.filter((w) => w.kind === KIND_CHAT).map((w) => w.id)}
                  contributions={contributions}
                />
              </div>
            ))}
          </div>
        </main>
      </div>
      <Modal
        open={aboutOpen}
        onClose={() => setAboutOpen(false)}
        title="О приложении"
        copyText={buildAboutCopyText(appAbout)}
      >
        <AboutContent about={appAbout} />
      </Modal>
      <Modal
        open={contributionModal.open}
        onClose={() => setContributionModal((m) => ({ ...m, open: false }))}
        title={contributionModal.title}
      >
        {contributionModal.body != null && <p className="modal-text">{contributionModal.body}</p>}
        <div className="modal-actions">
          {contributionModal.buttons.map((btn, i) => (
            <button
              key={i}
              type="button"
              className={btn.danger ? 'modal-action--danger' : ''}
              onClick={() => {
                if (btn.action) callAction(btn.action, btn.payload ?? {}).catch(() => {})
                setContributionModal((m) => ({ ...m, open: false }))
              }}
            >
              {btn.label ?? 'OK'}
            </button>
          ))}
          {contributionModal.buttons.length === 0 && (
            <button type="button" onClick={() => setContributionModal((m) => ({ ...m, open: false }))}>
              Закрыть
            </button>
          )}
        </div>
      </Modal>
    </div>
  )
}
