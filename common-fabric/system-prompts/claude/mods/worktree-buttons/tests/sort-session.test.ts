import { expect, mock, test } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { On } from 'claude-code'

type Group = { id: string; name: string }

// The session as get_session reports it. A group of undefined leaves the key
// out, as the app does before its window has reported the sidebar's groups.
type Session = { title: string; group?: Group | null | string; pinned?: boolean }

type Sidebar = {
  // This session, or the text get_session answers in its place.
  session: Session | string
  // What list_sections answers.
  sections: unknown
  // The desktop app's calls the mod made, as "server tool".
  calls: string[]
  moves: { session_ids: unknown; section_id: unknown }[]
  toasts: string[]
  // Lets the sorting a call started finish.
  clock: MockClock
  // The error move_sessions answers with, if it fails.
  moveFails?: string
  // When set, get_session answers with the session as it was when asked,
  // once the clock moves on by a millisecond.
  slowAnswer?: boolean
}

const SECTIONS: readonly { id: string; kind: string; name: string; shown?: boolean }[] = [
  { id: 'pinned', kind: 'pinned', name: '' },
  { id: 'cg-watch', kind: 'manual', name: '👀' },
  { id: 'cg-busy', kind: 'manual', name: 'Busy 🧱 🚧' },
  { id: 'cg-review', kind: 'manual', name: '🐤' },
  { id: 'cg-build', kind: 'manual', name: '🧱' },
  { id: 'cg-paused', kind: 'manual', name: '⏸️' },
  { id: 'cg-urgent', kind: 'manual', name: 'Urgent ❤️‍🔥' },
  { id: 'cg-old-heart', kind: 'manual', name: 'Old ❤', shown: false },
  { id: 'cg-heart', kind: 'manual', name: '✋🏽 ❤' },
  { id: 'cg-arc', kind: 'manual', name: 'Arc: Blocked upstream' },
  { id: 'sessions', kind: 'sessions', name: '' },
]

// This session's id, as the desktop app gives it to the session's process.
const SELF = 'local_self'

function group(id: string): Group {
  const section = SECTIONS.find(candidate => candidate.id === id)
  if (section === undefined) {
    throw new Error(`no section ${id}`)
  }
  return { id, name: section.name }
}

function reply(value: unknown, isError = false) {
  return { value: { content: [{ type: 'text' as const, text: typeof value === 'string' ? value : JSON.stringify(value) }], isError } }
}

// Stands in for the desktop app's session and sidebar tools, and for the
// parts of the host the worktree buttons read, which find no title. Outside
// the desktop app, the host session id is not set.
function host(on: On, session: Session | string, { inApp = true, moveFails }: { inApp?: boolean; moveFails?: string } = {}): Sidebar {
  const sidebar: Sidebar = { session, sections: SECTIONS, calls: [], moves: [], toasts: [], clock: mock.clock(on), moveFails }
  on('env.get', (_, e) => ({ value: inApp && e.name === 'CLAUDE_CODE_HOST_SESSION_ID' ? SELF : undefined }))
  on('ui.toast', (_, e) => {
    sidebar.toasts.push(e.text)
    return { value: undefined }
  })
  // A call that sets the title "refused" is denied, and one that sets the
  // title "broken" fails.
  on('tool.call', (_, e) => {
    const title = 'title' in e ? e.title : undefined
    if (title === 'refused') {
      return { deny: 'not allowed' }
    }
    return title === 'broken' ? { result: {}, isError: true as const } : { result: {} }
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('mcp.call', (_, { server, tool, args }) => {
    sidebar.calls.push(`${server} ${tool}`)
    switch (`${server} ${tool}`) {
      case 'ccd_session_mgmt get_session': {
        expect(args).toEqual({ session_id: 'self' })
        const answer = reply(typeof sidebar.session === 'string' ? sidebar.session : { sessionId: SELF, ...sidebar.session })
        return sidebar.slowAnswer ? sidebar.clock.sleep(1).then(() => answer) : answer
      }
      case 'ccd_sidebar list_sections':
        return reply(sidebar.sections)
      case 'ccd_sidebar move_sessions':
        if (sidebar.moveFails !== undefined) {
          return reply(sidebar.moveFails, true)
        }
        sidebar.moves.push({ session_ids: args.session_ids, section_id: args.section_id })
        return reply('Moved 1 session(s) to the section.')
    }
    throw new Error(`unexpected call ${server} ${tool}`)
  })
  return sidebar
}

async function start($: Engine, sidebar: Sidebar) {
  await $.session.start({ cwd: '/', surface: null, isInteractive: false })
  await sidebar.clock.settle()
}

async function detach($: Engine, sidebar: Sidebar, sessionId = 'self') {
  await $.tool.call({ tool: 'mcp__ccd_session_mgmt__detach_session', session_id: sessionId })
  await sidebar.clock.settle()
}

// Sets this session's title, and its section when one is given, then has
// the session make the call that sets the title, naming the session.
async function retitle($: Engine, sidebar: Sidebar, title: string, section?: Group | null | string, sessionId = 'self', settle = true) {
  sidebar.session = { ...(typeof sidebar.session === 'object' ? sidebar.session : {}), title }
  if (section !== undefined) {
    // A section of a string stands for a group the app describes as that
    // string.
    sidebar.session.group = section
  }
  await $.tool.call({ tool: 'mcp__ccd_session_mgmt__set_session_title', session_id: sessionId, title })
  if (settle) {
    await sidebar.clock.settle()
  }
}

const moved = (section_id: string) => ({ session_ids: ['self'], section_id })

test('a starting session is filed under the first section whose name has its state', async ($, on) => {
  const sidebar = host(on, { title: 'D0, ℂ4: 🧱 Fix the flake', group: null })
  await start($, sidebar)
  expect(sidebar.moves).toEqual([moved('cg-busy')])
  expect(sidebar.toasts).toEqual([])
})

test('a title without worktrees starts with its state', async ($, on) => {
  const sidebar = host(on, { title: '🐤 Answer a question: 🧱 or not', group: null })
  await start($, sidebar)
  expect(sidebar.moves).toEqual([moved('cg-review')])
})

test('setting the title files the session under its new state, and leaves it when no section has the state', async ($, on) => {
  const sidebar = host(on, { title: '💬 Starting', group: group('cg-watch') })
  await start($, sidebar)
  expect(sidebar.moves).toEqual([])

  await retitle($, sidebar, 'settings: 🐤 Sort sessions')
  expect(sidebar.moves).toEqual([moved('cg-review')])

  await retitle($, sidebar, 'settings: 🦚 Sort sessions', group('cg-review'))
  await retitle($, sidebar, 'settings: 🐤 Sort sessions', group('cg-review'))
  expect(sidebar.moves).toEqual([moved('cg-review')])
  expect(sidebar.toasts).toEqual([])
})

test('a state matches a section name with or without its variation selectors', async ($, on) => {
  const sidebar = host(on, { title: '💬 Starting', group: null })
  await start($, sidebar)
  for (const title of ['⏸ Waiting', 'D0: ⏸️ Waiting', '❤️‍🔥 Hot', '❤‍🔥 Hot']) {
    await retitle($, sidebar, title, null)
  }
  expect(sidebar.moves).toEqual([moved('cg-paused'), moved('cg-paused'), moved('cg-urgent'), moved('cg-urgent')])
})

test('a state matches only a whole emoji in a section the sidebar shows', async ($, on) => {
  const sidebar = host(on, { title: '💬 Starting', group: null })
  await start($, sidebar)
  for (const title of ['❤ Love', '✋ Wait', '✋🏽 Wait']) {
    await retitle($, sidebar, title, null)
  }
  expect(sidebar.moves).toEqual([moved('cg-heart'), moved('cg-heart')])
})

test('a session stays where it is in an Arc section, when pinned, with no state, or before its section is known', async ($, on) => {
  const sidebar = host(on, { title: 'D0: 🧱 Arc work', group: group('cg-arc') })
  await start($, sidebar)
  sidebar.session = { title: '🧱 Pinned', group: null, pinned: true }
  await retitle($, sidebar, '🧱 Pinned')
  sidebar.session = { title: 'PR: fix 🧱 flake', group: null }
  await retitle($, sidebar, 'PR: fix 🧱 flake')
  sidebar.session = { title: '🧱 Before the window reported groups' }
  await retitle($, sidebar, '🧱 Before the window reported groups')
  expect(sidebar.moves).toEqual([])

  sidebar.session = { title: 'PR: 🧱 fix flake', group: group('cg-watch') }
  await retitle($, sidebar, 'PR: 🧱 fix flake')
  expect(sidebar.moves).toEqual([moved('cg-busy')])
  expect(sidebar.toasts).toEqual([])
})

test('moving this session to the top level of the sidebar sorts it', async ($, on) => {
  const sidebar = host(on, { title: '💬 Child', group: null })
  await start($, sidebar)
  sidebar.session = { title: 'D1: 🐤 Child', group: null }
  await detach($, sidebar)
  expect(sidebar.moves).toEqual([moved('cg-review')])
})

test('a call that names another session, or that fails, sorts nothing', async ($, on) => {
  const sidebar = host(on, { title: '💬 Parent', group: null })
  await start($, sidebar)
  const before = sidebar.calls.length
  sidebar.session = { title: '🧱 Parent', group: null }
  await detach($, sidebar, 'local_child')
  await $.tool.call({ tool: 'mcp__ccd_session_mgmt__set_session_title', session_id: 'local_child', title: '🐤 Child' })
  await sidebar.clock.settle()
  for (const title of ['refused', 'broken']) {
    await $.tool.call({ tool: 'mcp__ccd_session_mgmt__set_session_title', session_id: 'self', title })
    await sidebar.clock.settle()
  }
  expect(sidebar.calls).toHaveLength(before)
  expect(sidebar.moves).toEqual([])

  await retitle($, sidebar, '🧱 Parent', undefined, SELF)
  expect(sidebar.moves).toEqual([moved('cg-busy')])
})

test('a session the desktop app did not start is never sorted', async ($, on) => {
  const sidebar = host(on, { title: '🧱 Work', group: null }, { inApp: false })
  await start($, sidebar)
  await retitle($, sidebar, '🐤 Work')
  await detach($, sidebar)
  expect(sidebar.calls).toEqual([])
  expect(sidebar.toasts).toEqual([])
})

test('a sort that fails says why, and later sorts still run', async ($, on) => {
  const sidebar = host(on, '{"sessionId":"local_self"}', { moveFails: 'No app window is open' })
  await start($, sidebar)
  sidebar.session = 'not JSON'
  await detach($, sidebar)
  await retitle($, sidebar, '🧱 Work', null)
  sidebar.sections = { sections: SECTIONS }
  await retitle($, sidebar, '🧱 Work')
  sidebar.sections = [{ kind: 'manual', name: '🧱' }]
  await retitle($, sidebar, '🧱 Work')
  sidebar.sections = SECTIONS
  await retitle($, sidebar, 'D0: 🧱 Arc work', 'cg-arc')
  sidebar.moveFails = undefined
  await retitle($, sidebar, '🧱 Work', null)
  expect(sidebar.toasts).toEqual([
    'Sorting the session into a section: get_session: no title',
    expect.stringMatching(/^Sorting the session into a section: .*JSON/u),
    'Sorting the session into a section: move_sessions: No app window is open',
    'Sorting the session into a section: list_sections: not a list of sections',
    'Sorting the session into a section: list_sections: not a list of sections',
    'Sorting the session into a section: get_session: a group that is not a section',
  ])
  expect(sidebar.moves).toEqual([moved('cg-busy')])
})

test('sorts run one after another, so the last title set decides', async ($, on) => {
  const sidebar = host(on, { title: '💬 Starting', group: null })
  await start($, sidebar)
  // The first sort asks about the session, and the answer arrives only after
  // the second title is set.
  sidebar.slowAnswer = true
  await retitle($, sidebar, '🐤 First', null)
  sidebar.slowAnswer = false
  await retitle($, sidebar, '🧱 Second', null, 'self', false)
  await sidebar.clock.advance(1)
  expect(sidebar.moves).toEqual([moved('cg-review'), moved('cg-busy')])
})
