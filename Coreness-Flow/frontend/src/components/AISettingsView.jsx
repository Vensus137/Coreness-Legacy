/**
 * Настройки AI: управление профилями агрегаторов (Polza.AI, OpenRouter, Custom).
 * Каждый профиль: name, aggregator, base_url, api_key, default_model.
 * Активный профиль используется плагином ai_service для completion.
 */

import { useState, useEffect, useCallback, useRef } from 'react'
import { getPluginSettings, setPluginSettings, callAction } from '../protocol'
import { IconEye, IconEyeOff } from './Icons'
import Tooltip from './Tooltip'
import './AISettingsView.css'

const PLUGIN_ID = 'ai_service'

function generateId() {
  return `p_${Date.now()}_${Math.random().toString(36).slice(2, 6)}`
}

function createEmptyProfile(aggregators, aggregatorId) {
  const agg = aggregators.find((a) => a.id === aggregatorId) || aggregators[0] || { id: 'custom', label: 'Custom', url: '', default_model: '' }
  return {
    id: generateId(),
    name: agg.label,
    aggregator: agg.id,
    base_url: agg.url,
    api_key: '',
    default_model: agg.default_model || '',
  }
}

// --- ModelCombobox ---

function ModelCombobox({ value, onChange, baseUrl, apiKey }) {
  const [input, setInput] = useState(value || '')
  const [models, setModels] = useState([])
  const [loading, setLoading] = useState(false)
  const [fetchError, setFetchError] = useState(null)
  const [open, setOpen] = useState(false)
  const wrapRef = useRef(null)
  const cacheKey = useRef('')

  const filtered = models.filter((m) => m.toLowerCase().includes(input.toLowerCase()))

  const MODELS_FETCH_TIMEOUT_MS = 8000

  const fetchModels = useCallback(async (url, key) => {
    if (!url) return
    const ck = `${url}::${key}`
    if (cacheKey.current === ck && models.length > 0) return
    setLoading(true)
    setFetchError(null)
    try {
      const timeoutPromise = new Promise((_, reject) => {
        setTimeout(() => reject(new Error('Таймаут загрузки списка моделей')), MODELS_FETCH_TIMEOUT_MS)
      })
      const res = await Promise.race([
        callAction('get_models', { base_url: url, api_key: key || '' }),
        timeoutPromise,
      ])
      if (res?.result === 'success') {
        cacheKey.current = ck
        setModels(res.response_data?.models || [])
      } else {
        setFetchError(res?.error?.message || 'Ошибка загрузки моделей')
      }
    } catch (e) {
      setFetchError(e?.message || 'Ошибка загрузки моделей')
    } finally {
      setLoading(false)
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [models.length])

  useEffect(() => {
    setInput(value || '')
  }, [value])

  useEffect(() => {
    const handleClick = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false)
      }
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [])

  const handleFocus = () => {
    setOpen(true)
    fetchModels(baseUrl, apiKey)
  }

  const handleSelect = (modelId) => {
    setInput(modelId)
    onChange(modelId)
    setOpen(false)
  }

  const handleInputChange = (e) => {
    const v = e.target.value
    setInput(v)
    onChange(v)
    setOpen(true)
  }

  const handleRefresh = () => {
    cacheKey.current = ''
    setModels([])
    fetchModels(baseUrl, apiKey)
  }

  return (
    <div className="ai-model-combobox" ref={wrapRef}>
      <div className="ai-model-combobox__input-row">
        <input
          type="text"
          className="ai-model-combobox__input"
          value={input}
          onChange={handleInputChange}
          onFocus={handleFocus}
          placeholder="Введите или выберите модель…"
          autoComplete="off"
        />
        <Tooltip text="Обновить список моделей">
          <button
            type="button"
            className={`ai-model-combobox__refresh${loading ? ' ai-model-combobox__refresh--loading' : ''}`}
            onClick={handleRefresh}
            disabled={!baseUrl || loading}
            aria-label="Обновить список моделей"
          >
            ↻
          </button>
        </Tooltip>
      </div>
      {open && (
        <div className="ai-model-combobox__dropdown">
          {loading && <div className="ai-model-combobox__status">Загрузка…</div>}
          {!loading && fetchError && (
            <div className="ai-model-combobox__status ai-model-combobox__status--error">{fetchError}</div>
          )}
          {!loading && !fetchError && !baseUrl && (
            <div className="ai-model-combobox__status">Укажите URL агрегатора</div>
          )}
          {!loading && !fetchError && models.length > 0 && filtered.length === 0 && (
            <div className="ai-model-combobox__status">Не найдено — введённое значение будет использовано</div>
          )}
          {!loading && !fetchError && filtered.map((m) => (
            <button
              key={m}
              type="button"
              className={`ai-model-combobox__option ${m === value ? 'ai-model-combobox__option--selected' : ''}`}
              onClick={() => handleSelect(m)}
            >
              {m}
            </button>
          ))}
        </div>
      )}
    </div>
  )
}

// --- TokenValidator ---

function TokenValidator({ baseUrl, apiKey }) {
  const [status, setStatus] = useState(null) // null | 'checking' | 'ok' | 'error'
  const [message, setMessage] = useState('')

  const handleCheck = async () => {
    if (!baseUrl || !apiKey) {
      setStatus('error')
      setMessage('Укажите URL и API-ключ')
      return
    }
    setStatus('checking')
    setMessage('')
    try {
      const res = await callAction('validate_token', { base_url: baseUrl, api_key: apiKey })
      if (res?.result === 'success') {
        const count = res.response_data?.models_count ?? 0
        setStatus('ok')
        setMessage(`Подключение OK · ${count} модел${count === 1 ? 'ь' : count < 5 ? 'и' : 'ей'} доступно`)
      } else {
        setStatus('error')
        setMessage(res?.error?.message || 'Ошибка проверки')
      }
    } catch (e) {
      setStatus('error')
      setMessage(e?.message || 'Ошибка проверки')
    }
  }

  return (
    <div className="ai-token-validator">
      <button
        type="button"
        className="ai-token-validator__btn"
        onClick={handleCheck}
        disabled={status === 'checking'}
      >
        {status === 'checking' ? 'Проверка…' : 'Проверить ключ'}
      </button>
      {status && status !== 'checking' && (
        <span className={`ai-token-validator__status ai-token-validator__status--${status}`}>
          {status === 'ok' ? '✓' : '✗'} {message}
        </span>
      )}
    </div>
  )
}

// --- ProfileCard ---

function ProfileCard({ profile, aggregators, isActive, isSelected, onClick }) {
  const agg = aggregators.find((a) => a.id === profile.aggregator)
  return (
    <button
      type="button"
      className={`ai-profile-card ${isSelected ? 'ai-profile-card--selected' : ''}`}
      onClick={onClick}
    >
      <div className="ai-profile-card__top">
        <span className="ai-profile-card__name">{profile.name || 'Без названия'}</span>
        {isActive && <span className="ai-profile-card__active-badge">Активный</span>}
      </div>
      <div className="ai-profile-card__meta">
        <span className="ai-profile-card__agg">{agg?.label || profile.aggregator}</span>
        <span className="ai-profile-card__model">{profile.default_model || '\u00A0'}</span>
      </div>
    </button>
  )
}

// --- ProfileEditor ---

function ProfileEditor({ profile, aggregators, isActive, onSave, onDelete, onActivate }) {
  const [draft, setDraft] = useState(profile)
  const [secretVisible, setSecretVisible] = useState(false)
  const [isDirty, setIsDirty] = useState(false)

  useEffect(() => {
    setDraft(profile)
    setIsDirty(false)
    setSecretVisible(false)
  }, [profile.id])

  const update = (key, value) => {
    setDraft((prev) => ({ ...prev, [key]: value }))
    setIsDirty(true)
  }

  const handleAggregatorChange = (aggId) => {
    const agg = aggregators.find((a) => a.id === aggId)
    if (!agg) return
    const prevAgg = aggregators.find((a) => a.id === draft.aggregator)
    const revertingToSaved = aggId === profile.aggregator
    setDraft((prev) => ({
      ...prev,
      aggregator: aggId,
      name: prev.name === prevAgg?.label ? agg.label : prev.name,
      base_url: revertingToSaved ? profile.base_url : (aggId !== 'custom' ? agg.url : prev.base_url),
      api_key: revertingToSaved ? profile.api_key : '',
      default_model: revertingToSaved ? profile.default_model : (agg.default_model || ''),
    }))
    setIsDirty(true)
  }

  const handleSave = () => {
    onSave(draft)
    setIsDirty(false)
  }

  const isCustom = draft.aggregator === 'custom'

  return (
    <div className="ai-profile-editor">
      <div className="ai-profile-editor__fields">

        <div className="ai-profile-editor__row">
          <label className="ai-profile-editor__label">Название профиля</label>
          <input
            type="text"
            className="ai-profile-editor__input"
            value={draft.name}
            onChange={(e) => update('name', e.target.value)}
            placeholder="Мой профиль"
          />
        </div>

        <div className="ai-profile-editor__row">
          <label className="ai-profile-editor__label">Агрегатор</label>
          <select
            className="ai-profile-editor__select"
            value={draft.aggregator}
            onChange={(e) => handleAggregatorChange(e.target.value)}
          >
            {aggregators.map((a) => (
              <option key={a.id} value={a.id}>{a.label}</option>
            ))}
          </select>
        </div>

        {isCustom && (
          <div className="ai-profile-editor__row">
            <label className="ai-profile-editor__label">URL агрегатора</label>
            <input
              type="text"
              className="ai-profile-editor__input"
              value={draft.base_url}
              onChange={(e) => update('base_url', e.target.value)}
              placeholder="https://api.example.com/v1"
            />
            <span className="ai-profile-editor__hint">
              OpenAI-совместимый API. https:// добавляется автоматически.
            </span>
          </div>
        )}

        <div className="ai-profile-editor__row">
          <label className="ai-profile-editor__label">API-ключ</label>
          <div className="ai-profile-editor__secret-wrap">
            <input
              type={secretVisible ? 'text' : 'password'}
              className="ai-profile-editor__input ai-profile-editor__input--secret"
              value={draft.api_key}
              onChange={(e) => update('api_key', e.target.value)}
              autoComplete="off"
              placeholder="sk-…"
            />
            <button
              type="button"
              className="ai-profile-editor__secret-toggle"
              onClick={() => setSecretVisible((v) => !v)}
              title={secretVisible ? 'Скрыть' : 'Показать'}
            >
              {secretVisible ? <IconEyeOff /> : <IconEye />}
            </button>
          </div>
          <TokenValidator baseUrl={draft.base_url} apiKey={draft.api_key} />
        </div>

        <div className="ai-profile-editor__row">
          <label className="ai-profile-editor__label">Модель по умолчанию</label>
          <ModelCombobox
            value={draft.default_model}
            onChange={(v) => update('default_model', v)}
            baseUrl={draft.base_url}
            apiKey={draft.api_key}
          />
        </div>
      </div>

      <div className="ai-profile-editor__actions">
        <button
          type="button"
          className="ai-profile-editor__btn ai-profile-editor__btn--primary"
          onClick={handleSave}
          disabled={!isDirty}
        >
          Сохранить
        </button>
        {!isActive && (
          <button
            type="button"
            className="ai-profile-editor__btn"
            onClick={() => onActivate(profile.id)}
          >
            Сделать активным
          </button>
        )}
        <button
          type="button"
          className="ai-profile-editor__btn ai-profile-editor__btn--delete"
          onClick={() => onDelete(profile.id)}
        >
          Удалить
        </button>
      </div>
    </div>
  )
}

// --- AISettingsView ---

export default function AISettingsView({ onClose }) {
  const [aggregators, setAggregators] = useState([])
  const [profiles, setProfiles] = useState([])
  const [activeProfileId, setActiveProfileId] = useState('')
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(true)
  const [loadError, setLoadError] = useState(null)
  const [saveStatus, setSaveStatus] = useState(null) // null | 'saving' | 'saved' | 'error'
  const saveStatusTimerRef = useRef(null)

  useEffect(() => {
    setLoading(true)
    setLoadError(null)
    Promise.all([
      callAction('get_aggregators', {}),
      getPluginSettings(PLUGIN_ID),
    ])
      .then(([aggsRes, settingsRes]) => {
        if (aggsRes?.result === 'success') {
          setAggregators(aggsRes.response_data?.aggregators || [])
        }
        if (settingsRes?.result === 'success') {
          const values = settingsRes.response_data?.values || {}
          try {
            const parsed = JSON.parse(values.profiles || '[]')
            const list = Array.isArray(parsed) ? parsed : []
            setProfiles(list)
            setActiveProfileId(values.active_profile_id || '')
            setSelectedId(list[0]?.id || null)
          } catch {
            setProfiles([])
          }
        } else {
          setLoadError(settingsRes?.error?.message || 'Не удалось загрузить профили')
        }
      })
      .catch((e) => setLoadError(e?.message || 'Ошибка загрузки'))
      .finally(() => setLoading(false))
  }, [])

  const saveToBackend = useCallback((newProfiles, newActiveId) => {
    setSaveStatus('saving')
    if (saveStatusTimerRef.current) clearTimeout(saveStatusTimerRef.current)
    setPluginSettings(PLUGIN_ID, {
      profiles: JSON.stringify(newProfiles),
      active_profile_id: newActiveId,
    })
      .then((res) => {
        setSaveStatus(res?.result === 'success' ? 'saved' : 'error')
        saveStatusTimerRef.current = setTimeout(() => setSaveStatus(null), 1500)
      })
      .catch(() => {
        setSaveStatus('error')
        saveStatusTimerRef.current = setTimeout(() => setSaveStatus(null), 1500)
      })
  }, [])

  const handleSaveProfile = useCallback((updatedProfile) => {
    const newProfiles = profiles.some((p) => p.id === updatedProfile.id)
      ? profiles.map((p) => (p.id === updatedProfile.id ? updatedProfile : p))
      : [...profiles, updatedProfile]
    setProfiles(newProfiles)
    saveToBackend(newProfiles, activeProfileId)
  }, [profiles, activeProfileId, saveToBackend])

  const handleDeleteProfile = useCallback((profileId) => {
    const newProfiles = profiles.filter((p) => p.id !== profileId)
    const newActiveId = activeProfileId === profileId ? (newProfiles[0]?.id || '') : activeProfileId
    setProfiles(newProfiles)
    setActiveProfileId(newActiveId)
    setSelectedId(newProfiles[0]?.id || null)
    saveToBackend(newProfiles, newActiveId)
  }, [profiles, activeProfileId, saveToBackend])

  const handleActivate = useCallback((profileId) => {
    setActiveProfileId(profileId)
    saveToBackend(profiles, profileId)
  }, [profiles, saveToBackend])

  const handleAddProfile = () => {
    const newProfile = createEmptyProfile(aggregators)
    const newProfiles = [...profiles, newProfile]
    setProfiles(newProfiles)
    setSelectedId(newProfile.id)
  }

  const selectedProfile = profiles.find((p) => p.id === selectedId) || null

  return (
    <div className="ai-settings-view">
      <header className="ai-settings-view__header workspace-sticky-header">
        <h2 className="ai-settings-view__title">AI</h2>
        <div className="ai-settings-view__header-actions">
          {saveStatus === 'saving' && <span className="ai-settings-view__status">Сохранение…</span>}
          {saveStatus === 'saved' && (
            <span className="settings-view-unified__saved" key="saved" aria-label="Сохранено">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </span>
          )}
          {saveStatus === 'error' && <span className="ai-settings-view__status ai-settings-view__status--err">Ошибка сохранения</span>}
          {onClose && (
            <Tooltip text="Закрыть">
              <button type="button" className="ai-settings-view__close" onClick={onClose}>
                Закрыть
              </button>
            </Tooltip>
          )}
        </div>
      </header>

      <div className="ai-settings-view__body">
        {loading && <div className="ai-settings-view__loading">Загрузка…</div>}
        {!loading && loadError && <div className="ai-settings-view__error">{loadError}</div>}
        {!loading && !loadError && (
          <div className="ai-settings-view__layout">

            <aside className="ai-settings-view__sidebar">
              <div className="ai-profile-list">
                {profiles.length === 0 && (
                  <p className="ai-profile-list__empty">Нет профилей. Добавьте первый.</p>
                )}
                {profiles.map((p) => (
                  <ProfileCard
                    key={p.id}
                    profile={p}
                    aggregators={aggregators}
                    isActive={p.id === activeProfileId}
                    isSelected={p.id === selectedId}
                    onClick={() => setSelectedId(p.id)}
                  />
                ))}
              </div>
              <button
                type="button"
                className="ai-settings-view__add-btn"
                onClick={handleAddProfile}
              >
                + Добавить профиль
              </button>
            </aside>

            <div className="ai-settings-view__editor">
              {selectedProfile ? (
                <ProfileEditor
                  key={selectedProfile.id}
                  profile={selectedProfile}
                  aggregators={aggregators}
                  isActive={selectedProfile.id === activeProfileId}
                  onSave={handleSaveProfile}
                  onDelete={handleDeleteProfile}
                  onActivate={handleActivate}
                />
              ) : (
                <div className="ai-settings-view__empty-editor">
                  {profiles.length === 0
                    ? 'Добавьте профиль агрегатора для работы AI'
                    : 'Выберите профиль для редактирования'}
                </div>
              )}
            </div>

          </div>
        )}
      </div>
    </div>
  )
}
