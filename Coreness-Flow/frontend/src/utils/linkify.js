/**
 * Разбивает текст на сегменты «текст» и «ссылка». Ссылка: начало с http://, https:// или www.;
 * конец — по первому вхождению пробела, переноса строки, < или > (чтобы не забирать теги в ссылку).
 * Также распознаётся markdown [текст](url).
 */

const MD_LINK_RE = /\[([^\]]*)\]\(([^)\s<>]+)\)/
const RAW_URL_RE = /(https?:\/\/|www\.)[^\s<>]+/

function safeHref(url) {
  const t = url.trim()
  if (/^https?:\/\//i.test(t)) return t
  if (/^www\./i.test(t)) return `https://${t}`
  return null
}

/**
 * Возвращает массив сегментов: { type: 'text', value } или { type: 'link', href, label }.
 */
export function linkifySegments(text) {
  if (typeof text !== 'string') return [{ type: 'text', value: '' }]
  const segments = []
  let pos = 0
  const s = text

  while (pos < s.length) {
    const fromPos = s.slice(pos)
    const mdMatch = fromPos.match(MD_LINK_RE)
    const rawMatch = fromPos.match(RAW_URL_RE)
    const mdStart = mdMatch ? pos + fromPos.indexOf(mdMatch[0]) : -1
    const rawStart = rawMatch ? pos + fromPos.search(RAW_URL_RE) : -1

    if (mdStart < 0 && rawStart < 0) {
      segments.push({ type: 'text', value: s.slice(pos) })
      break
    }

    let useMd = false
    let linkStart = 0
    let linkEnd = 0
    let href = ''
    let label = ''

    if (mdStart >= 0 && (rawStart < 0 || mdStart <= rawStart)) {
      const full = s.slice(mdStart).match(MD_LINK_RE)
      linkStart = mdStart
      linkEnd = mdStart + full[0].length
      const url = safeHref(full[2])
      if (url) {
        useMd = true
        href = url
        label = full[1] || full[2]
      }
    }

    if (!useMd && rawStart >= 0) {
      const full = s.slice(rawStart).match(RAW_URL_RE)[0]
      linkStart = rawStart
      linkEnd = rawStart + full.length
      href = safeHref(full) || full
      label = full
    }

    if (linkStart > pos) {
      segments.push({ type: 'text', value: s.slice(pos, linkStart) })
    }
    if (href) {
      segments.push({ type: 'link', href, label })
    } else if (linkEnd > pos) {
      segments.push({ type: 'text', value: s.slice(linkStart, linkEnd) })
    }
    pos = linkEnd > pos ? linkEnd : pos
  }

  return segments
}
