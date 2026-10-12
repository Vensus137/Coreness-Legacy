/**
 * Точка контрибьюта sidebar: подготовка списка пунктов для левой панели.
 * Объединяет встроенные пункты, пункты workspace и contributions.sidebar.
 * Компонент Sidebar в components/ только рендерит переданный список.
 */

/**
 * Строит полный список пунктов сайдбара: встроенные (История чатов), workspace-контрибьюты, contributions.sidebar.
 * @param {{ workspace: array, sidebar: array }} contributions — из get_contributions
 * @returns {{ type: 'builtin'|'workspace'|'sidebar', ... }[]} — список для Sidebar
 */
export function getSidebarItems(contributions) {
  const workspace = contributions?.workspace ?? []
  const sidebar = contributions?.sidebar ?? []
  // «История чатов» вынесена в иконку в шапке сайдбара
  const workspaceItems = workspace.map((c) => ({ type: 'workspace', ...c }))
  const sidebarItems = sidebar.map((c) => ({ type: 'sidebar', ...c }))
  return [...workspaceItems, ...sidebarItems]
}
