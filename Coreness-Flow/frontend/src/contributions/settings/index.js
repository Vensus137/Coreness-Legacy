/**
 * Точка контрибьюта settings: секции в общих настройках (вкладка по шестерёнке).
 * Секции сортируются по order, затем по pluginId для детерминированного порядка.
 */

const DEFAULT_ORDER = 0

/**
 * Возвращает отсортированный список секций настроек для единой вкладки «Настройки».
 * @param {{ settings?: Array<{ pluginId: string, label?: string, order?: number, fields: Array }> }} contributions
 * @returns {Array<{ pluginId: string, label?: string, order: number, fields: Array }>}
 */
export function getSettingsSections(contributions) {
  const list = contributions?.settings ?? []
  return [...list]
    .map((s) => ({ ...s, order: typeof s.order === 'number' ? s.order : DEFAULT_ORDER }))
    .sort((a, b) => a.order - b.order || (a.pluginId || '').localeCompare(b.pluginId || ''))
}
