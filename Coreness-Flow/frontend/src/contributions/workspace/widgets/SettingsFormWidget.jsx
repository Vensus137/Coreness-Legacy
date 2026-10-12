/**
 * Виджет формы настроек плагина (content.widget === "settingsForm" или секция в contributes.settings).
 * embedded: без кнопки «Сохранить», родитель вызывает save через registerSaveHandler; onDirty — при изменении поля.
 * Секретные поля (schema[key].secret): маска звёздочками и переключатель показать/скрыть.
 */

import { useState, useEffect, useRef, useCallback } from 'react'
import { getPluginSettings, setPluginSettings } from '../../../protocol'
import { IconEye, IconEyeOff } from '../../../components/Icons'
import './SettingsFormWidget.css'

/** Плейсхолдер, который бэкенд отдаёт вместо значения секретного поля; при сохранении не перезаписываем. */
const SECRET_PLACEHOLDER = '••••••••'

function getFieldLabel(field, schemaKey) {
  if (field.label) return field.label
  const spec = schemaKey && typeof schemaKey === 'object' ? schemaKey : {}
  return spec.description || field.key
}

function inputByType(key, spec, value, onChange, fieldId, isSecret, secretVisible, onToggleSecret) {
  const id = fieldId || `setting-${key}`
  if (isSecret) {
    return (
      <div className="settings-form-widget__secret-wrap">
        <input
          type={secretVisible ? 'text' : 'password'}
          value={value ?? ''}
          onChange={(e) => onChange(key, e.target.value)}
          className="settings-form-widget__input settings-form-widget__input--secret"
          id={id}
          autoComplete="off"
        />
        <button
          type="button"
          className="settings-form-widget__secret-toggle"
          onClick={onToggleSecret}
          title={secretVisible ? 'Скрыть' : 'Показать'}
          aria-label={secretVisible ? 'Скрыть' : 'Показать'}
        >
          {secretVisible ? <IconEyeOff /> : <IconEye />}
        </button>
      </div>
    )
  }
  if (spec?.type === 'boolean') {
    return (
      <input
        type="checkbox"
        checked={!!value}
        onChange={(e) => onChange(key, e.target.checked)}
        className="settings-form-widget__input settings-form-widget__checkbox"
        id={id}
      />
    )
  }
  if (spec?.type === 'integer') {
    return (
      <input
        type="number"
        value={value ?? ''}
        onChange={(e) => {
          const v = e.target.value === '' ? undefined : parseInt(e.target.value, 10)
          onChange(key, Number.isNaN(v) ? undefined : v)
        }}
        className="settings-form-widget__input"
        id={id}
        min={spec?.min}
        max={spec?.max}
      />
    )
  }
  if (spec?.type === 'array') {
    const str = Array.isArray(value) ? value.join(', ') : (value ?? '')
    return (
      <input
        type="text"
        value={str}
        onChange={(e) => {
          const raw = e.target.value
          const arr = raw ? raw.split(',').map((s) => s.trim()).filter(Boolean) : []
          onChange(key, arr)
        }}
        className="settings-form-widget__input"
        id={id}
        placeholder="Через запятую"
      />
    )
  }
  return (
    <input
      type="text"
      value={value ?? ''}
      onChange={(e) => onChange(key, e.target.value)}
      className="settings-form-widget__input"
      id={id}
    />
  )
}

export default function SettingsFormWidget({ pluginId, content, embedded, onDirty, registerSaveHandler }) {
  const fields = content?.fields || []
  const [schema, setSchema] = useState(null)
  const [values, setValues] = useState(null)
  const [visibleSecrets, setVisibleSecrets] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [saveMessage, setSaveMessage] = useState(null)
  const [saveMessageFading, setSaveMessageFading] = useState(false)
  const submitButtonRef = useRef(null)
  const isSavingRef = useRef(false)
  const dirtyRef = useRef(false)
  const saveFnRef = useRef(null)

  const toggleSecretVisible = useCallback((key) => {
    setVisibleSecrets((prev) => ({ ...prev, [key]: !prev[key] }))
  }, [])

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    setError(null)
    getPluginSettings(pluginId)
      .then((res) => {
        if (cancelled) return
        if (res?.result === 'success' && res?.response_data) {
          setSchema(res.response_data.schema || {})
          setValues(res.response_data.values != null ? { ...res.response_data.values } : {})
        } else {
          setError(res?.error?.message || 'Не удалось загрузить настройки')
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err?.message || 'Ошибка загрузки')
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => { cancelled = true }
  }, [pluginId])

  useEffect(() => {
    if (!saveMessage) return
    setSaveMessageFading(false)
    const t1 = setTimeout(() => setSaveMessageFading(true), 2000)
    const t2 = setTimeout(() => {
      setSaveMessage(null)
      setSaveMessageFading(false)
    }, 2500)
    return () => {
      clearTimeout(t1)
      clearTimeout(t2)
    }
  }, [saveMessage])

  const updateValue = useCallback((key, val) => {
    setValues((prev) => (prev ? { ...prev, [key]: val } : { [key]: val }))
    setSaveMessage(null)
    dirtyRef.current = true
    onDirty?.()
  }, [onDirty])

  const performSave = useCallback(() => {
    if (!values || isSavingRef.current) return Promise.resolve()
    const toSend = {}
    fields.forEach((f) => {
      const key = f.key
      if (!key || values[key] === undefined) return
      const spec = schema?.[key]
      if (spec?.secret && values[key] === SECRET_PLACEHOLDER) return
      toSend[key] = values[key]
    })
    isSavingRef.current = true
    submitButtonRef.current?.classList.add('settings-form-widget__submit--saving')
    setSaveMessage(null)
    return setPluginSettings(pluginId, toSend)
      .then((res) => {
        if (res?.result === 'success') {
          dirtyRef.current = false
          setSaveMessage('Сохранено')
        } else {
          setSaveMessage(res?.error?.message || 'Ошибка сохранения')
        }
      })
      .catch((err) => {
        setSaveMessage(err?.message || 'Ошибка сохранения')
      })
      .finally(() => {
        submitButtonRef.current?.classList.remove('settings-form-widget__submit--saving')
        isSavingRef.current = false
      })
  }, [pluginId, fields, values, schema])

  saveFnRef.current = performSave

  useEffect(() => {
    if (!embedded || !registerSaveHandler) return
    registerSaveHandler(pluginId, {
      isDirty: () => dirtyRef.current,
      save: () => saveFnRef.current?.(),
    })
  }, [embedded, registerSaveHandler, pluginId])

  const handleSubmit = (e) => {
    e.preventDefault()
    performSave()
  }

  if (loading) {
    return <div className="settings-form-widget settings-form-widget--loading">Загрузка…</div>
  }
  if (error) {
    return <div className="settings-form-widget settings-form-widget--error">{error}</div>
  }
  if (!fields.length) {
    return <div className="settings-form-widget settings-form-widget--empty">Нет полей для отображения.</div>
  }

  const fieldIdPrefix = embedded ? `setting-${pluginId}-` : 'setting-'
  return (
    <div className="settings-form-widget">
      <form onSubmit={handleSubmit} className="settings-form-widget__form">
        {fields.map((field) => {
          const key = field.key
          const spec = schema[key]
          const value = values?.[key]
          const label = getFieldLabel(field, spec)
          const isCheckbox = spec?.type === 'boolean'
          const isSecret = spec?.secret === true
          const fieldId = `${fieldIdPrefix}${key}`
          return (
            <div key={key} className={`settings-form-widget__row ${isCheckbox ? 'settings-form-widget__row--checkbox' : ''} ${isSecret ? 'settings-form-widget__row--secret' : ''}`}>
              {!isCheckbox && (
                <label htmlFor={fieldId} className="settings-form-widget__label">
                  {label}
                </label>
              )}
              {inputByType(key, spec, value, updateValue, fieldId, isSecret, visibleSecrets[key], () => toggleSecretVisible(key))}
              {isCheckbox && (
                <label htmlFor={fieldId} className="settings-form-widget__label">
                  {label}
                </label>
              )}
            </div>
          )
        })}
        {!embedded && (
          <div className="settings-form-widget__actions">
            <button ref={submitButtonRef} type="submit" className="settings-form-widget__submit">
              Сохранить
            </button>
            <span className="settings-form-widget__message-slot">
              {saveMessage && (
                <span
                  className={`settings-form-widget__message ${saveMessageFading ? 'settings-form-widget__message--fade-out' : ''}`}
                >
                  {saveMessage === 'Сохранено' ? (
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                      <path d="M20 6L9 17l-5-5" />
                    </svg>
                  ) : saveMessage}
                </span>
              )}
            </span>
          </div>
        )}
      </form>
    </div>
  )
}
