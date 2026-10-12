/**
 * Верхняя полоса (как Obsidian): тонкая зона перетаскивания сверху, под нею — сайдбар-кнопка, табы, кнопки окна.
 * Табы «наезжают» на тайтл; сверху остаётся полоска для перетаскивания.
 */

import { useState, useEffect, useRef } from 'react'
import {
  IconPanelLeftClose,
  IconPanelLeftOpen,
  IconMinus,
  IconMaximize2,
  IconMinimize2,
  IconX,
  IconInfo,
  IconRotateCcw,
  IconCheck,
} from './Icons'
import Tooltip from './Tooltip'
import { callAction } from '../protocol'

const hasElectron = typeof window !== 'undefined' && window.electronAPI

export default function TitleBar({
  sidebarOpen,
  onSidebarToggle,
  onOpenAbout,
  tabBar,
}) {
  const [isMaximized, setIsMaximized] = useState(false)
  const [configRefreshing, setConfigRefreshing] = useState(false)
  const [configSuccess, setConfigSuccess] = useState(false)
  const successTimeoutRef = useRef(null)

  useEffect(() => {
    return () => {
      if (successTimeoutRef.current) clearTimeout(successTimeoutRef.current)
    }
  }, [])

  const handleRefreshConfig = async () => {
    if (configRefreshing) return
    setConfigRefreshing(true)
    setConfigSuccess(false)
    try {
      const [scenariosRes, storageRes] = await Promise.all([
        callAction('sync_scenarios', { force_reload: true }),
        callAction('sync_storage', {}),
      ])
      const scenariosOk = scenariosRes?.result === 'success'
      const storageOk = storageRes?.result === 'success'
      if (scenariosOk && storageOk) {
        setConfigSuccess(true)
        if (successTimeoutRef.current) clearTimeout(successTimeoutRef.current)
        successTimeoutRef.current = setTimeout(() => {
          setConfigSuccess(false)
          successTimeoutRef.current = null
        }, 1500)
      } else {
        if (!scenariosOk) console.warn('Обновление сценариев:', scenariosRes?.error?.message || scenariosRes?.error)
        if (!storageOk) console.warn('Обновление storage:', storageRes?.error?.message || storageRes?.error)
      }
    } finally {
      setConfigRefreshing(false)
    }
  }

  useEffect(() => {
    if (!hasElectron) return
    window.electronAPI.isMaximized().then(setIsMaximized)
    const unsub = window.electronAPI.onMaximizedChange(setIsMaximized)
    return unsub
  }, [])

  const handleMinimize = () => hasElectron && window.electronAPI.minimize()
  const handleMaximize = () => hasElectron && window.electronAPI.maximize()
  const handleClose = () => hasElectron && window.electronAPI.close()

  return (
    <header className={`app-header title-bar ${sidebarOpen ? '' : 'title-bar--sidebar-closed'}`}>
      <div className="title-bar-row">
        {/* Нижний слой: зона 44px / ширина сайдбара, внутри — только иконки (справка и т.д.) */}
        <div className={`title-bar-left-area ${sidebarOpen ? 'title-bar-left-area--open' : ''}`}>
          {onOpenAbout && (
            <Tooltip text="Справка">
              <button
                type="button"
                className="title-bar-btn"
                onClick={onOpenAbout}
                aria-label="Справка"
              >
                <IconInfo />
              </button>
            </Tooltip>
          )}
          <Tooltip text={configSuccess ? 'Конфигурация обновлена' : configRefreshing ? 'Обновление…' : 'Обновить конфигурацию'}>
            <button
              type="button"
              className={`title-bar-btn ${configRefreshing ? 'title-bar-btn--loading' : ''} ${configSuccess ? 'title-bar-btn--success' : ''}`}
              onClick={handleRefreshConfig}
              disabled={configRefreshing}
              aria-label="Обновить конфигурацию"
            >
              <span className="title-bar-btn-icon-wrap">
                {configSuccess ? <IconCheck /> : <IconRotateCcw />}
              </span>
            </button>
          </Tooltip>
        </div>
        {/* Верхний слой: кнопка сворачивания поверх; при сворачивании заезжает влево и перекрывает иконки */}
        <div className={`title-bar-collapse-layer ${sidebarOpen ? 'title-bar-collapse-layer--open' : ''}`}>
          <Tooltip text={sidebarOpen ? 'Скрыть панель' : 'Показать панель'}>
            <button
              type="button"
              className="title-bar-btn"
              onClick={onSidebarToggle}
            >
              {sidebarOpen ? <IconPanelLeftClose /> : <IconPanelLeftOpen />}
            </button>
          </Tooltip>
        </div>
        {/* Шторка: привязана к левому краю элемента с кнопкой (left: 0), ширина 200px, поверх заголовка, под вкладками, drag всегда */}
        <div className="title-bar-curtain" aria-hidden />
        <div className="title-bar-tabs">
          {tabBar}
        </div>
        <div className="title-bar-right">
          {hasElectron && (
            <>
              <Tooltip text="Свернуть">
                <button type="button" className="title-bar-btn title-bar-btn-win" onClick={handleMinimize}>
                  <IconMinus />
                </button>
              </Tooltip>
              <Tooltip text={isMaximized ? 'Восстановить' : 'Развернуть'}>
                <button type="button" className="title-bar-btn title-bar-btn-win" onClick={handleMaximize}>
                  {isMaximized ? <IconMinimize2 /> : <IconMaximize2 />}
                </button>
              </Tooltip>
              <Tooltip text="Закрыть">
                <button type="button" className="title-bar-btn title-bar-btn-win title-bar-btn-close" onClick={handleClose}>
                  <IconX />
                </button>
              </Tooltip>
            </>
          )}
        </div>
      </div>
    </header>
  )
}
