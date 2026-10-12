/**
 * Контент воркспейса плагина: рендер по дескриптору из config.contributes (контрибьют).
 * По content.widget подключается виджет: settingsForm, vectorStoreAdmin и др.
 */

import SettingsFormWidget from '../contributions/workspace/widgets/SettingsFormWidget'
import VectorStoreAdminView from './VectorStoreAdminView'

export default function PluginWorkspaceView({ workspace, isActive, refreshTrigger, onClose }) {
  const { title, pluginId, content } = workspace
  const widget = content?.widget

  if (widget === 'settingsForm' && pluginId) {
    return (
      <div className="plugin-workspace-view settings-view">
        {title && <h2 className="plugin-workspace-view__title">{title}</h2>}
        <SettingsFormWidget pluginId={pluginId} content={content} />
      </div>
    )
  }

  if (widget === 'vectorStoreAdmin') {
    return <VectorStoreAdminView workspace={workspace} isActive={isActive} refreshTrigger={refreshTrigger} onClose={onClose} />
  }

  return (
    <div className="plugin-workspace-view settings-view">
      <h2>{title ?? pluginId}</h2>
      <p className="plugin-workspace-view__hint">Контент по дескриптору плагина — в разработке.</p>
    </div>
  )
}
