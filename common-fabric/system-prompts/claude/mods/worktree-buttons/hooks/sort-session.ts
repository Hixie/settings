import type { EngineInterface, ToolCallResult } from 'claude-code'

import { message } from './message.js'
import { emojiIn, parseTitle } from './title.js'

// Files this session in the desktop app's sidebar under the section for its
// state: the first section, in sidebar order, that the sidebar shows and whose
// name contains the state emoji of the session's title. The session stays
// where it is when no such section exists, when its section's name starts
// with "Arc:", when it is pinned, or when the app has not reported its
// section. A session the desktop app did not start, such as one in a
// terminal, is never sorted.

// This session's id, when the desktop app started it.
export function hostSession($: EngineInterface) {
  return $.env.get('CLAUDE_CODE_HOST_SESSION_ID')
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

// Whether a value describes a sidebar section, as list_sections and
// get_session's group do.
function isSection(value: unknown): value is Record<string, unknown> & { id: string; name: string } {
  return isObject(value) && typeof value.id === 'string' && typeof value.name === 'string'
}

// Calls a tool of one of the desktop app's MCP servers, and answers its text.
async function call($: EngineInterface, server: string, tool: string, args: Record<string, unknown>) {
  const { content, isError } = await $.mcp.call(server, tool, args)
  const text = content.flatMap(block => (block.type === 'text' ? [block.text] : [])).join('')
  if (isError) {
    throw new Error(`${tool}: ${text}`)
  }
  return text
}

// Calls a tool that answers in JSON.
async function read($: EngineInterface, server: string, tool: string, args: Record<string, unknown>): Promise<unknown> {
  return JSON.parse(await call($, server, tool, args))
}

async function sortSession($: EngineInterface) {
  if ((await hostSession($)) === undefined) {
    return
  }
  const session = await read($, 'ccd_session_mgmt', 'get_session', { session_id: 'self' })
  if (!isObject(session) || typeof session.title !== 'string') {
    throw new Error('get_session: no title')
  }
  if (session.pinned === true || !('group' in session)) {
    return
  }
  const { group } = session
  if (group !== null && !isSection(group)) {
    throw new Error('get_session: a group that is not a section')
  }
  const state = parseTitle(session.title)?.state
  if (state === undefined || group?.name.startsWith('Arc:')) {
    return
  }
  const sections = await read($, 'ccd_sidebar', 'list_sections', {})
  if (!Array.isArray(sections) || !sections.every(isSection)) {
    throw new Error('list_sections: not a list of sections')
  }
  const section = sections.find(({ name, shown }) => shown !== false && emojiIn(name).includes(state))
  if (section !== undefined && section.id !== group?.id) {
    await call($, 'ccd_sidebar', 'move_sessions', { session_ids: ['self'], section_id: section.id })
  }
}

async function sortOnce($: EngineInterface) {
  try {
    await sortSession($)
  } catch (error) {
    $.ui.toast(`Sorting the session into a section: ${message(error)}`)
  }
}

let sorting = Promise.resolve()

// Sorts this session once any sort already under way has finished, and says
// why when this one fails.
export function sort($: EngineInterface) {
  sorting = sorting.then(() => sortOnce($))
}

// Sorts this session once a tool call that named it has succeeded, and
// answers the call's result.
export async function sortAfter($: EngineInterface, sessionId: string, result: ToolCallResult) {
  const isThis = sessionId === 'self' || sessionId === (await hostSession($))
  if (isThis && result.deny === undefined && result.isError !== true) {
    sort($)
  }
  return result
}
