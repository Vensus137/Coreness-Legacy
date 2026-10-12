/**
 * Обёртка контента воркспейса: скролл скраю (зона .workspace-content-scroll), рабочая область 800px (inner).
 * Опциональный footer (например панель ввода чата) — в потоке снизу, скроллится только контент выше.
 * ref пробрасывается на элемент скролла (для чата — scroll-to-bottom). См. CONTRIBUTION_REFERENCE.md.
 */

import { forwardRef } from 'react'
import { mergeWithLayoutDefaults } from './defaults'

const WRAPPER_CLASS = 'workspace-content-frame'
const SCROLL_CLASS = 'workspace-content-scroll'
const INNER_CLASS = 'workspace-content-inner'
const FOOTER_CLASS = 'workspace-content-footer'

const WorkspaceLayout = forwardRef(function WorkspaceLayout({ children, layout, footer, scrollOverlay }, ref) {
  const opts = mergeWithLayoutDefaults(layout)

  const style = {
    '--workspace-top-padding': opts.topPadding,
    '--workspace-content-max-width': opts.contentMaxWidth,
    '--workspace-top-shadow-height': opts.topShadow ? `${opts.topShadowHeight}px` : '0',
  }

  const hasFooter = footer != null
  return (
    <div className={WRAPPER_CLASS + (hasFooter ? ' workspace-content-frame--has-footer' : '')} style={style}>
      <div ref={ref} className={SCROLL_CLASS}>
        <div className={INNER_CLASS}>{children}</div>
      </div>
      {footer != null && <div className={FOOTER_CLASS}>{footer}</div>}
      {scrollOverlay}
    </div>
  )
})

export default WorkspaceLayout
