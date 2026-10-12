/**
 * Вкладка управления векторной базой (Qdrant): список чанков, удаление по document_id.
 * Обновление: при переключении на вкладку (refreshTrigger) и по событию vector_store:chunks_changed.
 * Тихий апдейт: state меняем только если данные изменились (без лишнего ре-рендера).
 */

import { useState, useEffect, useCallback } from 'react'
import { callAction } from '../protocol'
import Tooltip from './Tooltip'
import Modal from './Modal'
import { IconTrash2 } from './Icons'
import './VectorStoreAdminView.css'

const PAGE_SIZE = 100
const TEXT_PREVIEW_LEN = 120

/** Формат даты: "ДД месяц ГГГГ г." (без дублирования "г." — локаль уже может добавлять). */
function formatIndexedDate(iso) {
  if (iso == null || iso === '') return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    const s = d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
    return s.endsWith(' г.') ? s : s + ' г.'
  } catch {
    try {
      const d = new Date(iso)
      return d.toLocaleDateString('ru-RU', { day: '2-digit', month: '2-digit', year: 'numeric' }).replace(/\//g, '.')
    } catch {
      return iso
    }
  }
}

/** Полная дата и время для модалки. */
function formatIndexedDateTime(iso) {
  if (iso == null || iso === '') return ''
  try {
    const d = new Date(iso)
    if (Number.isNaN(d.getTime())) return iso
    const datePart = d.toLocaleDateString('ru-RU', { day: '2-digit', month: 'long', year: 'numeric' })
    const timePart = d.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
    const dateStr = datePart.endsWith(' г.') ? datePart : datePart + ' г.'
    return `${dateStr}, ${timePart}`
  } catch {
    return iso
  }
}

function pointsEqual(a, b) {
  if (!Array.isArray(a) || !Array.isArray(b) || a.length !== b.length) return false
  return a.every((p, i) => b[i] && p.point_id === b[i].point_id)
}

function infoEqual(a, b) {
  if (a == null && b == null) return true
  if (a == null || b == null) return false
  return (a.points_count ?? null) === (b.points_count ?? null) && (a.collection_name ?? '') === (b.collection_name ?? '')
}

export default function VectorStoreAdminView({ workspace, isActive, refreshTrigger, onClose }) {
  const [info, setInfo] = useState(null)
  const [points, setPoints] = useState([])
  const [nextOffset, setNextOffset] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [deletingId, setDeletingId] = useState(null)
  const [detail, setDetail] = useState(null)

  const title = workspace?.title ?? 'Векторная база'

  const loadPage = useCallback(async (offset = null, silent = false) => {
    if (!silent) setLoading(true)
    setError(null)
    try {
      const payload = { limit: PAGE_SIZE }
      if (offset) payload.offset = offset
      const res = await callAction('list_chunks', payload)
      if (res?.result !== 'success') {
        setError(res?.error?.message || 'Ошибка загрузки')
        return
      }
      const data = res?.response_data || {}
      const newInfo = data.info || null
      const newPoints = data.points || []
      const newNextOffset = data.next_offset || null
      setInfo((prev) => (infoEqual(prev, newInfo) ? prev : newInfo))
      setPoints((prev) => {
        const merged = offset ? [...prev, ...newPoints] : newPoints
        const sorted = merged.slice().sort((a, b) =>
          (b.payload?.indexed_at || '').localeCompare(a.payload?.indexed_at || '')
        )
        return pointsEqual(prev, sorted) ? prev : sorted
      })
      setNextOffset(newNextOffset)
    } catch (e) {
      setError(e?.message || 'Ошибка загрузки')
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    if (isActive && refreshTrigger != null) loadPage(null, true)
  }, [isActive, refreshTrigger, loadPage])

  const handleLoadMore = () => nextOffset && loadPage(nextOffset, false)

  const handleDeleteDocument = useCallback(async (documentId) => {
    if (!documentId) return
    setDeletingId(documentId)
    setError(null)
    try {
      const res = await callAction('delete_chunks', { document_ids: [documentId] })
      if (res?.result !== 'success') {
        setError(res?.error?.message || 'Ошибка удаления')
      }
      // Обновление списка — по событию vector_store:chunks_changed с бэкенда
    } catch (e) {
      setError(e?.message || 'Ошибка удаления')
    } finally {
      setDeletingId(null)
    }
  }, [])

  const openDetail = useCallback((p) => {
    const docId = p.payload?.original_id ?? p.payload?.document_id ?? p.point_id
    const meta = { ...(p.payload || {}) }
    delete meta.text
    delete meta.original_id
    delete meta.document_id
    setDetail({
      documentId: docId,
      text: p.payload?.text ?? '',
      metadata: meta,
      indexedAt: p.payload?.indexed_at ?? null,
    })
  }, [])

  const textPreview = (text) => {
    if (text == null) return ''
    const s = String(text)
    return s.length <= TEXT_PREVIEW_LEN ? s : s.slice(0, TEXT_PREVIEW_LEN) + '…'
  }

  const detailCopyText = detail
    ? `document_id: ${detail.documentId}${detail.indexedAt != null ? `\nИндексирован: ${formatIndexedDateTime(detail.indexedAt)}` : ''}\n\nТекст:\n${detail.text}\n\nМетаданные:\n${JSON.stringify(detail.metadata, null, 2)}`
    : null

  return (
    <div className="vector-store-admin">
      <header className="vector-store-admin__header workspace-sticky-header">
        <h2 className="vector-store-admin__title">{title}</h2>
        <div className="vector-store-admin__actions">
          {onClose && (
            <Tooltip text="Закрыть">
              <button type="button" className="vector-store-admin__close" onClick={onClose}>
                Закрыть
              </button>
            </Tooltip>
          )}
        </div>
      </header>
      <div className="vector-store-admin__body">
        {error && <p className="vector-store-admin__error">{error}</p>}
        {points.length === 0 && !loading && (
          <p className="vector-store-admin__empty">Нет записей. Добавьте чанки через сценарии или действия.</p>
        )}
        {points.length > 0 && (
          <div className="vector-store-admin__list">
            {points.map((p) => {
              const docId = p.payload?.original_id ?? p.payload?.document_id ?? p.point_id
              const meta = { ...(p.payload || {}) }
              delete meta.text
              delete meta.original_id
              delete meta.document_id
              const metaStr = Object.keys(meta).length ? JSON.stringify(meta, null, 2) : '—'
              const indexedAt = p.payload?.indexed_at
              const collectionName = info?.collection_name ?? ''
              return (
                <div
                  key={p.point_id}
                  className="vector-store-admin__chunk"
                  onClick={() => openDetail(p)}
                >
                  <Tooltip text={metaStr} bubbleClassName="tooltip-bubble--multiline">
                    <div className="vector-store-admin__chunk-content">
                      <div className="vector-store-admin__chunk-head">
                        <span className="vector-store-admin__chunk-date">{indexedAt ? formatIndexedDate(indexedAt) : '—'}</span>
                        {collectionName && <span className="vector-store-admin__chunk-collection">{collectionName}</span>}
                      </div>
                      <div className="vector-store-admin__chunk-text">{p.payload?.text ?? ''}</div>
                    </div>
                  </Tooltip>
                  <div className="vector-store-admin__chunk-delete-wrap" onClick={(e) => e.stopPropagation()}>
                    <button
                      type="button"
                      className="vector-store-admin__chunk-delete"
                      onClick={(e) => { e.stopPropagation(); handleDeleteDocument(docId) }}
                      disabled={deletingId === docId}
                      title="Удалить чанк"
                      aria-label="Удалить"
                    >
                      {deletingId === docId ? <span className="vector-store-admin__chunk-delete-loading">…</span> : <IconTrash2 />}
                    </button>
                  </div>
                </div>
              )
            })}
          </div>
        )}
        {nextOffset && (
          <div className="vector-store-admin__more">
            <button type="button" className="vector-store-admin__btn" onClick={handleLoadMore} disabled={loading}>
              Ещё
            </button>
          </div>
        )}
      </div>

      <Modal
        open={detail != null}
        onClose={() => setDetail(null)}
        title="Текст и метаданные"
        copyText={detailCopyText}
        panelClassName="modal-panel--wide"
      >
        {detail && (
          <div className="vector-store-admin__detail">
            <p className="vector-store-admin__detail-label">document_id</p>
            <p className="vector-store-admin__detail-value vector-store-admin__detail-id">{detail.documentId}</p>
            {detail.indexedAt != null && (
              <>
                <p className="vector-store-admin__detail-label">Индексирован</p>
                <p className="vector-store-admin__detail-value vector-store-admin__detail-date">{formatIndexedDateTime(detail.indexedAt)}</p>
              </>
            )}
            <p className="vector-store-admin__detail-label">Текст</p>
            <pre className="vector-store-admin__detail-value vector-store-admin__detail-text">{detail.text || '—'}</pre>
            <p className="vector-store-admin__detail-label">Метаданные</p>
            <pre className="vector-store-admin__detail-value vector-store-admin__detail-meta">
              {Object.keys(detail.metadata).length ? JSON.stringify(detail.metadata, null, 2) : '—'}
            </pre>
          </div>
        )}
      </Modal>
    </div>
  )
}
