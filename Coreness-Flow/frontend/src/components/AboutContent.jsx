/**
 * Контент блока «О приложении» для модального окна.
 * Данные приходят с бэка (get_app_metadata.response_data.about).
 */

const UNAVAILABLE_MESSAGE = 'Данные о приложении недоступны'

/** Собирает текст для копирования в буфер из массива about (label: value или value). При отсутствии данных — нейтральное сообщение. */
export function buildAboutCopyText(about) {
  if (!Array.isArray(about) || about.length === 0) {
    return UNAVAILABLE_MESSAGE
  }
  const lines = []
  about.forEach((item) => {
    if (item?.label != null && (item?.value != null || item?.href != null)) {
      lines.push(`${item.label}: ${item.value ?? item.href ?? ''}`)
    }
  })
  return lines.length > 0 ? lines.join('\n') : UNAVAILABLE_MESSAGE
}

export default function AboutContent({ about }) {
  if (about === null) {
    return (
      <div className="about-content">
        <p className="about-loading">Загрузка…</p>
      </div>
    )
  }

  if (!Array.isArray(about) || about.length === 0) {
    return (
      <div className="about-content">
        <p className="about-unavailable">{UNAVAILABLE_MESSAGE}</p>
      </div>
    )
  }

  return (
    <div className="about-content">
      <dl className="about-list">
        {about.map((item, i) => (
          <span key={item.label ?? i}>
            <dt>{item.label}</dt>
            <dd>
              {item.href ? (
                <a
                  href={item.href}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="about-link"
                >
                  {item.value ?? item.href}
                </a>
              ) : (
                item.value ?? '—'
              )}
            </dd>
          </span>
        ))}
      </dl>
    </div>
  )
}
