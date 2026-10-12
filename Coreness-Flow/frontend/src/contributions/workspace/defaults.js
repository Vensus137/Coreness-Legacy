/**
 * Дефолты опций layout для воркспейсов (как у чата). Контрибьют может переопределять через contributes.workspace.layout.
 * См. CONTRIBUTION_REFERENCE.md.
 */

export const LAYOUT_DEFAULTS = {
  topPadding: 32,
  topShadow: true,
  topShadowHeight: 28,
  contentMaxWidth: '800px',
}

/**
 * Нормализует значение из контрибьюта в CSS-пригодное (число → px, строка как есть).
 */
export function normalizeLayout(layout) {
  if (!layout || typeof layout !== 'object') return {}
  const out = {}
  if (layout.topPadding !== undefined) {
    out.topPadding = typeof layout.topPadding === 'number' ? `${layout.topPadding}px` : String(layout.topPadding)
  }
  if (layout.topShadow !== undefined) {
    out.topShadow = !!layout.topShadow
    out.topShadowHeight =
      layout.topShadow === false ? 0 : typeof layout.topShadow === 'number' ? layout.topShadow : layout.topShadowHeight ?? 28
  }
  if (layout.contentMaxWidth !== undefined) {
    out.contentMaxWidth =
      typeof layout.contentMaxWidth === 'number' ? `${layout.contentMaxWidth}px` : String(layout.contentMaxWidth)
  }
  return out
}

export function mergeWithLayoutDefaults(layout) {
  const normalized = normalizeLayout(layout)
  return {
    topPadding: normalized.topPadding ?? `${LAYOUT_DEFAULTS.topPadding}px`,
    topShadow: normalized.topShadow !== false,
    topShadowHeight: normalized.topShadowHeight ?? LAYOUT_DEFAULTS.topShadowHeight,
    contentMaxWidth: normalized.contentMaxWidth ?? LAYOUT_DEFAULTS.contentMaxWidth,
  }
}
