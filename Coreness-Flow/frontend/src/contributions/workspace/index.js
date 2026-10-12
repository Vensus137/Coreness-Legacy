/**
 * Точка контрибьюта workspace: дефолты layout, обёртка WorkspaceLayout.
 * Реестр типов — в WorkspaceContent (встроенные chat, settings, chat_list; остальное — плагин).
 */

export { LAYOUT_DEFAULTS, mergeWithLayoutDefaults, normalizeLayout } from './defaults'
export { default as WorkspaceLayout } from './WorkspaceLayout'
