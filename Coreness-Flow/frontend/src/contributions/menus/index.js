/**
 * Точка контрибьюта menus: только данные из контрибьюта.
 * Встроенные пункты (Настройки, О приложении) добавляются в компоненте Sidebar, не здесь.
 */

/**
 * Пункты меню шестерёнки сайдбара из контрибьюта (contributions.menus.sidebarHeader).
 * Встроенные пункты добавляет App. Возвращаемые элементы — с полем builtIn: false для единообразия.
 * @param {{ sidebarHeader?: array }} contributionsMenus — contributions.menus
 * @returns {array} — элементы { builtIn: false, pluginId, id, label, action }
 */
export function getHeaderMenuItems(contributionsMenus) {
  const items = contributionsMenus?.sidebarHeader ?? []
  return items.map((it) => ({ ...it, builtIn: false }))
}

/**
 * Дополнительные пункты контекстного меню вкладки (после встроенного «Переименовать»).
 * App объединяет со встроенными. Элементы с полем builtIn: false для единообразия.
 * @param {{ tabContextMenu?: array }} contributionsMenus — contributions.menus
 * @returns {array} — элементы { builtIn: false, pluginId, id, label, action }
 */
export function getTabContextMenuExtraItems(contributionsMenus) {
  const items = contributionsMenus?.tabContextMenu ?? []
  return items.map((it) => ({ ...it, builtIn: false }))
}
