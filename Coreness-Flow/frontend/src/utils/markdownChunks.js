/**
 * Разбиение markdown на блоки по границам узлов AST (параграф, код, список и т.д.)
 * Чанки в диапазоне minChars..maxChars; блоки больше maxChars (например код) не делятся.
 */

import { unified } from 'unified'
import remarkParse from 'remark-parse'
import remarkGfm from 'remark-gfm'
import remarkStringify from 'remark-stringify'
import { toString } from 'mdast-util-to-string'

const MIN_CHARS = 80
const MAX_CHARS = 320

let parseProcessor = null
let stringifyProcessor = null

function getParseProcessor() {
  if (!parseProcessor) {
    parseProcessor = unified().use(remarkParse).use(remarkGfm)
  }
  return parseProcessor
}

function getStringifyProcessor() {
  if (!stringifyProcessor) {
    stringifyProcessor = unified().use(remarkStringify)
  }
  return stringifyProcessor
}

/** Сериализует один узел или массив узлов обратно в markdown. */
function nodesToMarkdown(nodes) {
  if (!nodes || nodes.length === 0) return ''
  const root = { type: 'root', children: Array.isArray(nodes) ? nodes : [nodes] }
  return getStringifyProcessor().stringify(root)
}

/**
 * Разбивает текст на массив markdown-строк (чанков). Каждый чанк — валидный markdown.
 * Чанки в диапазоне minChars..maxChars; блок больше maxChars (напр. код) остаётся одним чанком.
 */
export function getMarkdownChunks(text, minChars = MIN_CHARS, maxChars = MAX_CHARS) {
  const trimmed = (text ?? '').trim()
  if (!trimmed) return []

  try {
    const ast = getParseProcessor().parse(trimmed)
    const nodes = ast?.children ?? []
    if (nodes.length === 0) return [trimmed]

    const stringify = getStringifyProcessor()
    const chunks = []
    let current = []
    let currentLen = 0

    for (const node of nodes) {
      const nodeMd = stringify.stringify({ type: 'root', children: [node] })
      const len = nodeMd.length

      if (len > maxChars) {
        if (current.length > 0) {
          chunks.push(nodesToMarkdown(current))
          current = []
          currentLen = 0
        }
        chunks.push(nodeMd)
        continue
      }

      if (currentLen + len > maxChars && current.length > 0) {
        chunks.push(nodesToMarkdown(current))
        current = []
        currentLen = 0
      }
      current.push(node)
      currentLen += len
    }

    if (current.length > 0) {
      chunks.push(nodesToMarkdown(current))
    }

    return chunks.length > 0 ? chunks : [trimmed]
  } catch {
    return [trimmed]
  }
}

/** Из markdown-строки извлекает plain text (без разметки). */
function markdownToPlainText(md) {
  if (!md || !md.trim()) return ''
  try {
    const ast = getParseProcessor().parse(md)
    return toString(ast)
  } catch {
    return md
  }
}

/**
 * Чанки с plain-текстом для эффекта печатания: сначала печатаем plain, затем показываем markdown.
 * @param {string} text — полный markdown
 * @param {number} minChars — минимальная длина чанка
 * @returns {{ markdown: string, plainText: string }[]}
 */
export function getChunksWithPlainText(text, minChars = MIN_CHARS, maxChars = MAX_CHARS) {
  const chunks = getMarkdownChunks(text, minChars, maxChars)
  return chunks.map((markdown) => ({
    markdown,
    plainText: markdownToPlainText(markdown),
  }))
}
