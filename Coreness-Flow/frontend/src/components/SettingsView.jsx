/**
 * Общие настройки: липкий заголовок (Настройки, Закрыть) и секции из contributes.settings.
 * Батч-сохранение по таймеру (500 ms), индикатор «Сохранено» с анимацией.
 */

import { useState, useRef, useCallback, useEffect } from 'react'
import { getSettingsSections } from '../contributions/settings'
import SettingsFormWidget from '../contributions/workspace/widgets/SettingsFormWidget'
import Tooltip from './Tooltip'
import './SettingsView.css'

const BATCH_DEBOUNCE_MS = 500
const SAVED_SHOW_MS = 1500

export default function SettingsView({ contributions, onClose }) {
  const sections = getSettingsSections(contributions || {})
  const handlersRef = useRef(new Map())
  const batchTimerRef = useRef(null)
  const [saveStatus, setSaveStatus] = useState(null) // null | 'saving' | 'saved'
  const savedHideTimerRef = useRef(null)

  const runBatchSave = useCallback(async () => {
    const handlers = handlersRef.current
    const toSave = []
    handlers.forEach((h, pluginId) => {
      if (h?.isDirty?.()) toSave.push({ pluginId, save: h.save })
    })
    if (toSave.length === 0) return
    setSaveStatus('saving')
    const promises = toSave.map(({ save }) => (typeof save === 'function' ? save() : Promise.resolve()))
    await Promise.all(promises)
    setSaveStatus('saved')
    savedHideTimerRef.current = setTimeout(() => setSaveStatus(null), SAVED_SHOW_MS)
  }, [])

  const scheduleBatchSave = useCallback(() => {
    if (batchTimerRef.current) clearTimeout(batchTimerRef.current)
    batchTimerRef.current = setTimeout(() => {
      batchTimerRef.current = null
      runBatchSave()
    }, BATCH_DEBOUNCE_MS)
  }, [runBatchSave])

  const registerSaveHandler = useCallback((pluginId, handler) => {
    handlersRef.current.set(pluginId, handler)
  }, [])

  useEffect(() => {
    return () => {
      if (batchTimerRef.current) clearTimeout(batchTimerRef.current)
      if (savedHideTimerRef.current) clearTimeout(savedHideTimerRef.current)
    }
  }, [])

  return (
    <div className="settings-view-unified">
      <header className="settings-view-unified__header workspace-sticky-header">
        <h2 className="settings-view-unified__title">Настройки</h2>
        <div className="settings-view-unified__actions">
          {saveStatus === 'saved' && (
            <span className="settings-view-unified__saved" key="saved" aria-label="Сохранено">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </span>
          )}
          {onClose && (
            <Tooltip text="Закрыть">
              <button type="button" className="settings-view-unified__close" onClick={onClose}>
                Закрыть
              </button>
            </Tooltip>
          )}
        </div>
      </header>
      <div className="settings-view-unified__body">
        {sections.length === 0 ? (
          <p className="settings-view-unified__empty">Нет секций настроек.</p>
        ) : (
          sections.map((section) => (
            <section key={section.pluginId} className="settings-view-unified__section">
              <h3 className="settings-view-unified__section-title">{section.label || section.pluginId}</h3>
              <SettingsFormWidget
                pluginId={section.pluginId}
                content={{ fields: section.fields }}
                embedded
                onDirty={scheduleBatchSave}
                registerSaveHandler={registerSaveHandler}
              />
            </section>
          ))
        )}
      </div>
    </div>
  )
}
