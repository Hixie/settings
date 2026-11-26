import { expect, mock, test } from 'claude-code/testing'
import type { Engine, MockClock } from 'claude-code/testing'
import type { On } from 'claude-code'

const HOME = '/home/hixie'
const CF = `${HOME}/dev/commonfabric`
const METADATA = `${HOME}/Library/Application Support/Claude/claude-code-sessions/account/organization/local_session.json`

const BAND = {
  plugin: 'worktree-buttons',
  component: 'AbovePrompt',
  requestId: 'above-prompt',
  props: {
    hasSurvey: false,
    isCollapsed: false,
    isWorking: false,
    maxRows: 10,
    bodyColumns: 80,
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

const SURFACES = ['terminal', 'desktop'] as const

type Checkout = {
  remotes: Record<string, string>
  branch: string | null
  commits: readonly string[]
  unfetched?: true
  // How merging the branch into the main branch goes, when it does not merge
  // cleanly.
  merge?: 'conflicts' | 'unrelated' | 'unmergeable'
}

type World = {
  title: string
  // The session's metadata file when it is not just the title, or null
  // before the desktop app has written it.
  metadata?: string | null
  // The pull request table, or null when the file does not exist.
  prs: string | null
  checkouts: Record<string, Checkout>
  // Folders that exist but are not git checkouts.
  folders?: readonly string[]
  // The session's working directory, once the session has started.
  cwd?: string
  ran: (readonly string[])[]
  home: string
  // How the commands a press runs fail, if they do.
  pressFails?: 'busy' | 'error'
  toasts: string[]
  runs: number
  // What the session was sent, and why it refuses to take messages, if it does.
  said: string[]
  refusesMessages?: string
  // When set, a message or a press's command is answered only once the test
  // moves this clock on by a millisecond.
  clock?: MockClock
  // When set, reading the pull request table, or the session's metadata file,
  // is answered only once the test moves this clock on by a millisecond.
  tableClock?: MockClock
  titleClock?: MockClock
}

async function held(world: World) {
  await world.clock?.sleep(1)
}

const LABS_REMOTES = {
  origin: 'git@github.com:hixie/labs.git',
  upstream: 'https://github.com/commonfabric/labs',
}

type Answer = { code: number; stdout?: string; stderr?: string }

const REPOSITORIES = ['labs', 'cfs', 'web-weaver', 'weaver', 'crm', 'specs'] as const

// Whether a folder or file exists: the root, the commonfabric folder, the
// repository folders, the checkouts, and the other folders. The volume ignores
// case, as macOS's does by default.
function exists(world: World, path: string) {
  const folded = path.toLowerCase()
  return [
    '/',
    `${world.home}/dev/commonfabric`,
    ...REPOSITORIES.map(repo => `${world.home}/dev/commonfabric/${repo}`),
    ...Object.keys(world.checkouts).flatMap(checkout => [checkout, `${checkout}/.git`]),
    ...(world.folders ?? []),
  ].some(existing => existing.toLowerCase() === folded)
}

// What the host's commands answer: the pull request table, the commands a
// press runs, and git in the checkouts that exist.
function answer(world: World, argv: readonly string[], cwd: string): Answer {
  const [command, ...args] = argv
  switch (command) {
    case 'lockf': {
      const table = `${world.home}/.cache/github-prs.tsv`
      expect(args).toEqual(['-kn', table, 'cat', table])
      if (world.prs === null) {
        return { code: 69, stderr: `lockf: ${table}: No such file or directory\n` }
      }
      return world.prs === 'unreadable' ? { code: 73, stderr: `lockf: cannot open ${table}: Permission denied\n` } : { code: 0, stdout: world.prs }
    }
    case `${world.home}/dev/contraptions/iterm-run/iterm-run`:
      world.ran.push(argv)
      if (world.pressFails === 'error') {
        return { code: 2, stderr: 'iterm-run: osascript failed: iTerm2 has no windows\n' }
      }
      return world.pressFails === 'busy' ? { code: 1, stdout: 'busy\n' } : { code: 0, stdout: 'ran\n' }
    case 'open':
      world.ran.push(argv)
      return world.pressFails === 'error' ? { code: 1, stderr: 'LSOpenURLsWithRole() failed with error -10814\n' } : { code: 0 }
    case 'git': {
      const checkout = world.checkouts[cwd]
      if (checkout === undefined) {
        throw new Error(`git outside a checkout: ${cwd}`)
      }
      const remotes = Object.entries(checkout.remotes)
      const comparison = `refs/remotes/${'upstream' in checkout.remotes ? 'upstream' : 'origin'}/main`
      switch (args[0]) {
        case 'config':
          return remotes.length === 0 ? { code: 1 } : { code: 0, stdout: remotes.map(([name, url]) => `remote.${name}.url ${url}\n`).join('') }
        case 'rev-list':
          expect(args).toEqual(['rev-list', '--reverse', '--topo-order', '--abbrev-commit', 'HEAD', '--not', comparison])
          return !checkout.unfetched
            ? { code: 0, stdout: checkout.commits.map(commit => `${commit}\n`).join('') }
            : { code: 128, stderr: `fatal: bad revision '^${args.at(-1)}'\n` }
        case 'merge-tree':
          expect(args).toEqual(['merge-tree', '--write-tree', '--quiet', comparison, 'HEAD'])
          expect(checkout.commits).not.toHaveLength(0)
          switch (checkout.merge) {
            case undefined:
              return { code: 0 }
            case 'conflicts':
              return { code: 1 }
            case 'unrelated':
              return { code: 128, stderr: 'fatal: refusing to merge unrelated histories\n' }
            case 'unmergeable':
              return { code: 1, stderr: `merge-tree: ${comparison} - not something we can merge\n` }
          }
        case 'symbolic-ref':
          return checkout.branch === null ? { code: 1 } : { code: 0, stdout: `${checkout.branch}\n` }
      }
    }
  }
  throw new Error(`unexpected command ${argv.join(' ')}`)
}

// Stands in for the host: the environment, the file system (only the
// repository folders, the checkouts, and the other folders exist), the
// commands the mod runs, and the session's prompt.
function host(on: On, world: World) {
  const env: Record<string, string> = {
    HOME: world.home,
    CLAUDE_CODE_ACCOUNT_UUID: 'account',
    CLAUDE_CODE_ORGANIZATION_UUID: 'organization',
    CLAUDE_CODE_HOST_SESSION_ID: 'local_session',
  }
  on('env.get', (_, e) => ({ value: env[e.name] }))
  on('fs.exists', (_, e) => ({
    value: e.path === METADATA.replace(HOME, world.home) ? world.metadata !== null : exists(world, e.path),
  }))
  on('fs.list', (_, e) => {
    expect(e.path).toBe(`${world.home}/dev/commonfabric`)
    return { value: REPOSITORIES.map(name => ({ name, kind: 'dir' as const, size: 0, mtimeMs: 0, isLink: false })) }
  })
  on('prompt.submit', async (_, e) => {
    expect(e.origin).toEqual({ kind: 'plugin', name: 'worktree-buttons', asUser: true })
    await held(world)
    if (world.refusesMessages !== undefined) {
      return { drop: world.refusesMessages }
    }
    world.said.push(e.text)
    return { text: e.text }
  })
  on('fs.read', async (_, e) => {
    await world.titleClock?.sleep(1)
    expect(e.path).toBe(METADATA.replace(HOME, world.home))
    expect(world.metadata).not.toBeNull()
    return { value: world.metadata ?? JSON.stringify({ sessionId: 'local_session', title: world.title }) }
  })
  on('ui.toast', (_, e) => {
    world.toasts.push(e.text)
    return { value: undefined }
  })
  // A command runs in the session's working directory unless it names one, and
  // fails to start, as posix_spawn does, in a folder that does not exist.
  on('process.spawn', async function* (_, { argv, cwd = world.cwd }) {
    world.runs += 1
    if (cwd === undefined || !exists(world, cwd)) {
      return { deny: `failed to start: ENOENT: no such file or directory, posix_spawn '${argv[0]}'` }
    }
    if (argv[0] === `${world.home}/dev/contraptions/iterm-run/iterm-run`) {
      await held(world)
    }
    if (argv[0] === 'lockf') {
      await world.tableClock?.sleep(1)
    }
    const result = answer(world, argv, cwd)
    if (result.stdout) {
      yield { stream: 'stdout' as const, text: result.stdout }
    }
    if (result.stderr) {
      yield { stream: 'stderr' as const, text: result.stderr }
    }
    return { value: { code: result.code, signal: null } }
  })
  // The engine's own band, drawn when the mod has nothing to show.
  on('ui.render', { component: 'AbovePrompt', plugin: 'worktree-buttons' }, ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  on('session.start', (_, e) => {
    world.cwd = e.cwd
    return { cwd: e.cwd }
  })
  on('session.attach', (_, e) => ({ clientId: e.clientId }))
  // The desktop app's record of the session, before its window has reported
  // the sidebar's sections, so the session is never sorted into one.
  on('mcp.call', () => ({
    value: { content: [{ type: 'text' as const, text: JSON.stringify({ title: world.title }) }], isError: false },
  }))
}

function world(title: string, checkouts: Record<string, Checkout>, prs: readonly string[] = []): World {
  return { title, prs: prs.join('\n'), checkouts, ran: [], home: HOME, toasts: [], runs: 0, said: [] }
}

async function start($: Engine) {
  await $.session.start({ cwd: CF, surface: null, isInteractive: false })
}

// The labels the band shows: buttons, then the dim text of errors.
async function labels($: Engine, surface: (typeof SURFACES)[number]) {
  const ui = await $.ui.mount({ ...BAND, surface })
  const buttons = (await ui.findAll({ type: 'Button' })).map(found => found.text)
  const texts = (await ui.findAll({ type: 'Text' })).map(found => found.text)
  await ui.unmount()
  return { buttons, texts }
}

async function press($: Engine, key: string) {
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  await ui.press({ key })
  await ui.unmount()
}

// A press that runs a command in the shell of iTerm2's frontmost session.
function iterm(command: string, home = HOME) {
  return [`${home}/dev/contraptions/iterm-run/iterm-run`, command]
}

test('a branch with commits and no pull request offers a review, and a squash when there are several', async ($, on) => {
  const w = world('D0, D1: 🧱 Fix the thing', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa', 'bbb'] },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'one', commits: ['ccc'] },
  })
  host(on, w)
  await start($)

  for (const surface of SURFACES) {
    expect(await labels($, surface)).toEqual({ buttons: ['D0: REVIEW (2 commits)', 'SQUASH', 'D1: REVIEW'], texts: [] })
  }
  await press($, 'D0')
  await press($, 'D1')
  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D0; c --separate`), iterm(`cd ${CF}/labs/D1; c --separate`)])
  expect(w.said).toEqual([])

  await press($, 'D0 SQUASH')
  expect(w.said).toEqual(['squash'])
  expect(w.ran).toHaveLength(2)

  w.refusesMessages = 'a Stop hook is blocking'
  await press($, 'D0 SQUASH')
  expect(w.toasts).toEqual(['D0: SQUASH: a Stop hook is blocking'])
})

test('a branch whose commits conflict with the main branch also offers a rebase, after any other dim button', async ($, on) => {
  const w = world('D0, D1, D2, D3, D4, D5, D6, D7: ✅ Fix the thing', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'one', commits: ['aaa'], merge: 'conflicts' },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'two', commits: ['bbb', 'ccc'], merge: 'conflicts' },
    [`${CF}/labs/D2`]: { remotes: LABS_REMOTES, branch: 'pr', commits: ['ddd'], merge: 'conflicts' },
    [`${CF}/labs/D3`]: { remotes: LABS_REMOTES, branch: 'more', commits: ['eee', 'fff', 'ggg'], merge: 'conflicts' },
    [`${CF}/labs/D4`]: { remotes: LABS_REMOTES, branch: 'clean', commits: ['hhh', 'iii'] },
    [`${CF}/labs/D5`]: { remotes: LABS_REMOTES, branch: 'unrelated', commits: ['jjj'], merge: 'unrelated' },
    [`${CF}/labs/D6`]: { remotes: LABS_REMOTES, branch: 'added', commits: ['kkk', 'lll'], merge: 'conflicts' },
    [`${CF}/labs/D7`]: { remotes: LABS_REMOTES, branch: 'odd', commits: ['mmm'], merge: 'unmergeable' },
  }, ['commonfabric/labs\tpr\t12', 'commonfabric/labs\tmore\t13', 'commonfabric/labs\tadded\t14'])
  host(on, w)
  await start($)

  for (const surface of SURFACES) {
    expect(await labels($, surface)).toEqual({
      buttons: [
        'D0: REVIEW', 'REBASE',
        'D1: REVIEW (2 commits)', 'SQUASH', 'REBASE',
        'D2: REREVIEW TO MERGE (PR #12)', 'REBASE',
        'D3: REVIEW TO MERGE (2 new commits, PR #13)', 'EACH COMMIT', 'REBASE',
        'D4: REVIEW (2 commits)', 'SQUASH',
        'D6: REVIEW TO MERGE (1 new commit, PR #14)', 'REBASE',
      ],
      // A failure that is not a conflict is reported in place of the buttons.
      texts: [
        'D5: ERROR: git merge-tree: fatal: refusing to merge unrelated histories',
        'D7: ERROR: git merge-tree: merge-tree: refs/remotes/upstream/main - not something we can merge',
      ],
    })
  }
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await ui.find({ key: 'D1 group' }))?.children).toHaveLength(3)
  await ui.unmount()

  await press($, 'D1 REBASE')
  await press($, 'D1 SQUASH')
  await press($, 'D3 REBASE')
  expect(w.said).toEqual(['rebase', 'squash', 'rebase'])
  await press($, 'D3 EACH COMMIT')
  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D3; c fff..ggg --separate`)])

  // A pull request that is not ready opens in the browser, with a rebase
  // beside it.
  w.title = 'D2: 🦚 Fix the thing'
  await $.session.attach({ surface: 'desktop', clientId: 'desktop:default' })
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D2: OPEN PR #12', 'REBASE'], texts: [] })
})

test('a press that has not finished shows its progress in place of its button', async ($, on) => {
  const w = world('D0: 🧱 Fix the thing', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa', 'bbb'] },
  })
  w.clock = mock.clock(on)
  host(on, w)
  await start($)
  const band = async (isWorking: boolean) => {
    // A second instance: press keeps its own mounted until the press finishes.
    // Each read waits for the mod while it is busy, so it is read once.
    const ui = await $.ui.mount({ ...BAND, requestId: 'look', props: { ...BAND.props, isWorking }, surface: 'desktop' })
    const found = await ui.findAll({})
    await ui.unmount()
    const of = (type: string) => found.filter(element => element.type === type).map(element => element.text)
    return { buttons: of('Button'), texts: of('Text') }
  }

  // A message waits for the session to be idle.
  let pressed = press($, 'D0 SQUASH')
  await w.clock.settle()
  expect(await band(true)).toEqual({ buttons: ['D0: REVIEW (2 commits)'], texts: ['SQUASH (sent when this turn ends)'] })
  expect(await band(false)).toEqual({ buttons: ['D0: REVIEW (2 commits)'], texts: ['SQUASH (sending)'] })
  expect(w.said).toEqual([])
  await w.clock.advance(1)
  await pressed
  expect(w.said).toEqual(['squash'])
  expect(await band(true)).toEqual({ buttons: ['D0: REVIEW (2 commits)', 'SQUASH'], texts: [] })

  pressed = press($, 'D0')
  await w.clock.settle()
  expect(await band(false)).toEqual({ buttons: ['SQUASH'], texts: ['D0: REVIEW (2 commits) (running)'] })
  expect(w.ran).toEqual([])
  await w.clock.advance(1)
  await pressed
  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D0; c --separate`)])
  expect(await band(false)).toEqual({ buttons: ['D0: REVIEW (2 commits)', 'SQUASH'], texts: [] })
})

// A session whose title the test changes with the tool that sets it, and
// whose band, on each surface, is mounted before the buttons are worked out
// again and read while that is under way. Each read waits for the mod while it
// is busy, so each drawing is read once.
async function spinnerSession($: Engine, on: On, title: string) {
  const w = world(title, {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  const clock = mock.clock(on)
  host(on, w)
  on('tool.call', () => ({ result: {} }))
  await start($)
  const uis = await Promise.all(SURFACES.map(surface => $.ui.mount({ ...BAND, requestId: `look ${surface}`, surface })))
  return {
    w,
    clock,
    retitle: (text: string) => {
      w.title = text
      return $.tool.call({ tool: 'mcp__ccd_session_mgmt__set_session_title', session_id: 'self', title: text })
    },
    // Whether each surface shows the spinner, which a surface may draw as
    // text, its buttons, and whether it shows the dim text of a press that
    // has not finished.
    bands: () =>
      Promise.all(uis.map(async ui => {
        const found = await ui.findAll({})
        return {
          spinner: found.some(element => element.text.includes('Checking worktrees')),
          buttons: found.filter(element => element.type === 'Button').map(element => element.text),
          pressing: found.some(element => /\((?:running|sending|sent when this turn ends)\)$/u.test(element.text)),
        }
      })),
    unmount: () => Promise.all(uis.map(ui => ui.unmount())),
  }
}

const both = <T,>(band: T) => [band, band]
const REVIEWING = both({ spinner: false, buttons: ['D0: REVIEW'], pressing: false })
const SPINNING = both({ spinner: true, buttons: [], pressing: false })
const EMPTY = both({ spinner: false, buttons: [], pressing: false })

test('while the buttons are worked out, a spinner shows in their place', async ($, on) => {
  const { w, clock, retitle, bands, unmount } = await spinnerSession($, on, 'D0: 🧱 Work')
  expect(await bands()).toEqual(REVIEWING)

  w.tableClock = clock
  const retitled = retitle('D0: 🐤 Work')
  await clock.settle()
  expect(await bands()).toEqual(SPINNING)
  await clock.advance(1)
  await retitled
  expect(await bands()).toEqual(REVIEWING)
  await unmount()
})

test('the spinner also takes the place of a press that has not finished', async ($, on) => {
  const { w, clock, retitle, bands, unmount } = await spinnerSession($, on, 'D0: 🧱 Work')

  // The press's command and the refresh are both held.
  w.clock = clock
  const pressed = press($, 'D0')
  await clock.settle()
  w.tableClock = clock
  const retitled = retitle('D0: 🐤 Work')
  await clock.settle()
  expect(await bands()).toEqual(SPINNING)
  w.clock = undefined
  w.tableClock = undefined
  await clock.advance(1)
  await Promise.all([pressed, retitled])
  expect(await bands()).toEqual(REVIEWING)
  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D0; c --separate`)])
  await unmount()
})

test('a title without worktrees never shows the spinner', async ($, on) => {
  const { w, clock, retitle, bands, unmount } = await spinnerSession($, on, '💬 Starting')

  // Held before the mod has read the title.
  w.titleClock = clock
  const retitled = retitle('💬 Still talking')
  await clock.settle()
  expect(await bands()).toEqual(EMPTY)
  await clock.advance(1)
  await retitled
  expect(await bands()).toEqual(EMPTY)
  await unmount()
})

test('a refresh that finishes after a newer one changes nothing', async ($, on) => {
  const { w, clock, retitle, bands, unmount } = await spinnerSession($, on, 'D0: 🧱 Work')

  // An older refresh held before it reads the title does not show the
  // spinner once a newer one has finished.
  w.titleClock = clock
  const older = retitle('D0: 🐤 Work')
  await clock.settle()
  w.titleClock = undefined
  await retitle('D0: 🦚 Work')
  await clock.advance(1)
  await older
  expect(await bands()).toEqual(REVIEWING)

  // An older refresh held after it has read a title naming D0 does not show
  // D0's buttons once a newer one has found no worktrees.
  w.tableClock = clock
  const stale = retitle('D0: 🐤 Work')
  await clock.settle()
  w.tableClock = undefined
  await retitle('💬 Done')
  await clock.advance(1)
  await stale
  expect(await bands()).toEqual(EMPTY)
  await unmount()
})

test('a branch with no commits of its own offers to open the worktree, pull request or not', async ($, on) => {
  const w = world('D0, D1: ✅ Answer a question', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'main', commits: [] },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'fix', commits: [] },
  }, ['commonfabric/labs\tfix\t12'])
  host(on, w)
  await start($)

  for (const surface of SURFACES) {
    expect(await labels($, surface)).toEqual({ buttons: ['D0: OPEN WORKTREE', 'D1: OPEN WORKTREE'], texts: [] })
  }
  await press($, 'D0')
  await press($, 'D1')
  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D0; l`), iterm(`cd ${CF}/labs/D1; l`)])
})

test('a missing pull request table means no pull requests', async ($, on) => {
  const w = world('D0: ✅ Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  w.prs = null
  host(on, w)
  await start($)

  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })
  await press($, 'D0')
  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D0; c --separate`)])
})

test('a pull request table that cannot be read is reported', async ($, on) => {
  const w = world('D0: ✅ Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  w.prs = 'unreadable'
  host(on, w)
  await start($)

  expect(await labels($, 'desktop')).toEqual({
    buttons: [],
    texts: [`worktree-buttons: lockf: cannot open ${HOME}/.cache/github-prs.tsv: Permission denied`],
  })
})

test('a ready pull request offers a review of the commits after the first, together or one at a time, or a merge', async ($, on) => {
  const w = world('D0, D1, ℂE3: ✅ Ship it', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa', 'bbb', 'ccc'] },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'two', commits: ['eee', 'fff'] },
    [`${CF}/cfs/E3`]: { remotes: { origin: 'git@github.com:commonfabric/cfs.git' }, branch: 'fix', commits: ['ddd'] },
  }, ['commonfabric/labs\tfix\t12', 'commonfabric/labs\ttwo\t13', 'commonfabric/cfs\tfix\t34'])
  host(on, w)
  await start($)

  for (const surface of SURFACES) {
    // A single new commit has no separate review of each commit.
    expect(await labels($, surface)).toEqual({
      buttons: ['D0: REVIEW TO MERGE (2 new commits, PR #12)', 'EACH COMMIT', 'D1: REVIEW TO MERGE (1 new commit, PR #13)', 'ℂE3: REREVIEW TO MERGE (PR #34)'],
      texts: [],
    })
  }
  // The two buttons of a worktree stay together when the row wraps.
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await ui.find({ key: 'D0 group' }))?.children).toHaveLength(2)
  expect((await ui.find({ key: 'D1 group' }))?.children).toHaveLength(1)
  await ui.unmount()
  await press($, 'D0')
  await press($, 'D0 EACH COMMIT')
  await press($, 'D1')
  await press($, 'ℂE3')
  expect(w.ran).toEqual([
    iterm(`cd ${CF}/labs/D0; c bbb..ccc`),
    iterm(`cd ${CF}/labs/D0; c bbb..ccc --separate`),
    iterm(`cd ${CF}/labs/D1; c fff..fff`),
    iterm(`cd ${CF}/cfs/E3; c`),
  ])
})

test('a pull request opens in the browser in any state but ✅', async ($, on) => {
  const w = world('', {
    [`${CF}/weaver/A1`]: {
      remotes: { origin: 'https://github.com/CommonFabric/weaver.git' },
      branch: 'feature',
      commits: ['aaa'],
    },
  }, ['commonfabric/weaver\tfeature\t7', 'commonfabric/weaver\tfeature\t9'])
  host(on, w)
  for (const state of ['🪻', '🦚', '🧱']) {
    w.title = `ωA1: ${state} Weaver work`
    w.ran = []
    await start($)

    expect(await labels($, 'desktop')).toEqual({ buttons: ['ωA1: OPEN PR #9'], texts: [] })
    await press($, 'ωA1')
    expect(w.ran).toEqual([['open', 'https://github.com/commonfabric/weaver/pull/9']])
  }
})

test('a pull request for another repository or branch does not count', async ($, on) => {
  host(on, world('settings, web-B2: ✅ Two things', {
    [`${HOME}/dev/settings`]: { remotes: { origin: 'git@github.com:Hixie/settings.git' }, branch: 'main', commits: ['aaa'] },
    [`${CF}/web-weaver/B2`]: { remotes: { origin: 'git@github.com:commonfabric/web-weaver.git' }, branch: 'b', commits: [] },
  }, ['hixie/other\tmain\t1', 'commonfabric/web-weaver\ta\t2']))
  await start($)

  expect(await labels($, 'desktop')).toEqual({ buttons: ['settings: REVIEW', 'web-B2: OPEN WORKTREE'], texts: [] })
})

test('a title without worktrees leaves the band to the engine', async ($, on) => {
  const w = world('', {})
  host(on, w)
  const titles = [
    '🧱 Fix: a bug in the parser',
    'Untitled session',
    '💬 Question',
    'PR: fix flake',
    '🐤 D0: 🧱 or not',
    '🐤 D0-1: 🧱 or not',
    '💬 Review PR-12: `draft`',
    'Bump node-20: (security)',
  ]
  for (const title of titles) {
    w.title = title
    await start($)

    expect(await labels($, 'desktop')).toEqual({ buttons: [], texts: ['engine'] })
  }
})

test('a worktree whose folder does not exist says so', async ($, on) => {
  const w = world('ZZ: 🧱 Gone', {})
  host(on, w)
  await start($)

  expect(await labels($, 'desktop')).toEqual({ buttons: [], texts: ['ZZ: FOLDER MISSING'] })
  expect(w.runs).toBe(1)
})

test('a session whose own worktree was deleted still shows and runs the others', async ($, on) => {
  const w = world('D0, D1: 🧱 Work', {
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'pr', commits: ['bbb'] },
  }, ['commonfabric/labs\tpr\t12'])
  host(on, w)
  await $.session.start({ cwd: `${CF}/labs/D0`, surface: null, isInteractive: false })

  expect(await labels($, 'desktop')).toEqual({ buttons: ['D1: OPEN PR #12'], texts: ['D0: FOLDER MISSING'] })
  await press($, 'D1')
  expect(w.ran).toEqual([['open', 'https://github.com/commonfabric/labs/pull/12']])
  expect(w.toasts).toEqual([])
})

test('a folder that is not a git checkout, such as dogfood, offers to open it', async ($, on) => {
  const w = world('dogfood, fishfood: 🧱 Update the builds', {})
  w.folders = [`${CF}/dogfood`, `${CF}/fishfood`]
  host(on, w)
  await start($)

  expect(await labels($, 'desktop')).toEqual({ buttons: ['dogfood: OPEN WORKTREE', 'fishfood: OPEN WORKTREE'], texts: [] })
  await press($, 'dogfood')
  await press($, 'fishfood')
  expect(w.ran).toEqual([iterm(`cd ${CF}/dogfood; l`), iterm(`cd ${CF}/fishfood; l`)])
})

test('lines of the pull request table that are not about a pull request are skipped', async ($, on) => {
  const w = world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  }, ['', 'commonfabric/labs fix 12', 'commonfabric/labs\tfix\t0', '\tfix\t13', 'commonfabric/labs\tfix\t14\textra', 'commonfabric/labs\tfix\t5'])
  host(on, w)
  await start($)

  await press($, 'D0')
  expect(w.ran).toEqual([['open', 'https://github.com/commonfabric/labs/pull/5']])
})

test('a session file the title is missing from, or that holds an escaped NUL, is read', async ($, on) => {
  const w = world('', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  w.metadata = '{"sessionId":"local_session"}'
  host(on, w)
  await start($)
  expect(await labels($, 'desktop')).toEqual({ buttons: [], texts: ['engine'] })

  w.metadata = '{"cwd":"a\\u0000b","title":"D0: \\ud83e\\uddf1 Work"}'
  await $.session.attach({ surface: 'desktop', clientId: 'desktop:default' })
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })
})

test('an empty item in the worktree list is skipped', async ($, on) => {
  host(on, world('D0,: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  }))
  await start($)

  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })
})

test('a worktree whose main branch was never fetched says so rather than counting nothing', async ($, on) => {
  host(on, world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'], unfetched: true },
  }))
  await start($)

  const { buttons, texts } = await labels($, 'desktop')
  expect(buttons).toEqual([])
  expect(texts).toEqual([expect.stringMatching(/^D0: ERROR: git rev-list: fatal: bad revision/u)])
})

test('a worktree path that the shell would split is quoted', async ($, on) => {
  const home = "/Users/o'brien smith"
  const w = world('D0: 🧱 Work', {
    [`${home}/dev/commonfabric/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  w.home = home
  host(on, w)
  await start($)

  await press($, 'D0')
  expect(w.ran).toEqual([iterm(`cd '/Users/o'\\''brien smith/dev/commonfabric/labs/D0'; c --separate`, home)])
})

test('a press says why nothing happened, and says nothing when it worked', async ($, on) => {
  const w = world('D0, D1: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'pr', commits: ['bbb'] },
  }, ['commonfabric/labs\tpr\t12'])
  host(on, w)
  await start($)

  await press($, 'D0')
  await press($, 'D1')
  expect(w.toasts).toEqual([])

  w.pressFails = 'busy'
  await press($, 'D0')
  expect(w.toasts).toEqual(['D0: REVIEW: busy'])

  w.pressFails = 'error'
  await press($, 'D0')
  await press($, 'D1')
  expect(w.toasts).toEqual([
    'D0: REVIEW: busy',
    'D0: REVIEW: iterm-run: osascript failed: iTerm2 has no windows',
    'D1: OPEN PR #12: LSOpenURLsWithRole() failed with error -10814',
  ])
  expect(w.ran).toHaveLength(5)
})

test('a pull request counts only in the repository of the upstream remote, or else origin', async ($, on) => {
  const w = world('D0, settings: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
    [`${HOME}/dev/settings`]: { remotes: { origin: 'git@github.com:Hixie/settings.git' }, branch: 'main', commits: ['bbb'] },
  }, ['commonfabric/labs\tfix\t12', 'hixie/labs\tfix\t99', 'Hixie/settings\tmain\t5'])
  host(on, w)
  await start($)

  await press($, 'D0')
  await press($, 'settings')
  expect(w.ran).toEqual([
    ['open', 'https://github.com/commonfabric/labs/pull/12'],
    ['open', 'https://github.com/Hixie/settings/pull/5'],
  ])
})

test('a press runs the command its button showed, then shows what changed', async ($, on) => {
  const w = world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa', 'bbb'] },
  })
  host(on, w)
  await start($)

  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await ui.findAll({ type: 'Button' })).map(found => found.text)).toEqual(['D0: REVIEW (2 commits)', 'SQUASH'])
  w.prs = 'commonfabric/labs\tfix\t12'
  await ui.press({ key: 'D0' })
  await ui.unmount()

  expect(w.ran).toEqual([iterm(`cd ${CF}/labs/D0; c --separate`)])
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: OPEN PR #12'], texts: [] })
  await press($, 'D0')
  expect(w.ran.at(-1)).toEqual(['open', 'https://github.com/commonfabric/labs/pull/12'])
})

test('a window attaching shows a title changed since', async ($, on) => {
  const w = world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'more', commits: [] },
  })
  host(on, w)
  await start($)
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })

  w.title = 'D0, D1: 🧱 Work'
  await $.session.attach({ surface: 'desktop', clientId: 'desktop:default' })
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW', 'D1: OPEN WORKTREE'], texts: [] })
})

test('a session that starts with no window attached has its buttons ready', async ($, on) => {
  host(on, world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  }))
  await $.session.start({ cwd: CF, surface: null, isInteractive: false })

  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })
})

test('worktree identifiers name the same folders as ~/bin/l does', async ($, on) => {
  const paths: Record<string, string> = {
    'ℂE3': `${CF}/cfs/E3`,
    'ℂe4': `${CF}/cfs/E4`,
    c1: `${CF}/cfs/1`,
    C1: `${CF}/labs/C1`,
    cfs: `${CF}/cfs/root`,
    crm: `${CF}/crm/root`,
    cRM: `${CF}/cfs/RM`,
    lf: `${CF}/labs/LF`,
    'ωA1': `${CF}/weaver/A1`,
    wb2: `${CF}/weaver/B2`,
    W2: `${CF}/labs/W2`,
    INFRA2: `${CF}/infra/2`,
    deno5: `${HOME}/dev/denoland/5`,
    cliffy: `${HOME}/dev/cliffy/root`,
    'cfs-K1': `${CF}/cfs/K1`,
    'loom-K2': `${CF}/loom/K2`,
    'weaver-C3': `${CF}/weaver/C3`,
    'commonfabric-weaver-C4': `${CF}/weaver/C4`,
    web: `${CF}/web-weaver/root`,
    'web-A1': `${CF}/web-weaver/A1`,
    'gvisor-82': `${CF}/gvisor/82`,
    labs: `${CF}/labs/root`,
    specs: `${CF}/specs/root`,
    L3: `${CF}/labs/L3`,
    d0: `${CF}/labs/D0`,
    contraptions: `${HOME}/dev/contraptions`,
    dogfood: `${CF}/dogfood`,
    fishfood: `${CF}/fishfood`,
  }
  const ids = Object.keys(paths)
  host(on, world(`${ids.join(', ')}, D0X, ℭE3, cE3X, 𝛌E5, λE6, lf2, D0: 🧱 Everything`, Object.fromEntries(
    Object.values(paths).map(path => [path, { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] }]),
  )))
  await start($)

  // D0X, ℭE3, cE3X, and the former cfs identifiers 𝛌E5, λE6, and lf2 are
  // not identifiers, loom is not another name for cfs, and D0 is the folder d0
  // already named.
  expect(await labels($, 'desktop')).toEqual({ buttons: ids.map(id => `${id}: REVIEW`), texts: [] })
})

test('a detached HEAD or a remote not on GitHub has no pull request', async ($, on) => {
  host(on, world('D0, gitlab-A1: ✅ Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: null, commits: ['aaa'] },
    [`${CF}/gitlab/A1`]: { remotes: { origin: 'git@gitlab.com:commonfabric/labs.git' }, branch: 'fix', commits: ['bbb'] },
  }, ['commonfabric/labs\tfix\t12']))
  await start($)

  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW', 'gitlab-A1: REVIEW'], texts: [] })
})

test('setting the session title shows the new worktrees', async ($, on) => {
  const w = world('💬 Starting', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  host(on, w)
  on('tool.call', () => ({ result: {} }))
  await start($)
  expect(await labels($, 'desktop')).toEqual({ buttons: [], texts: ['engine'] })

  w.title = 'D0: 🧱 Work'
  await $.tool.call({ tool: 'mcp__ccd_session_mgmt__set_session_title', session_id: 'self', title: w.title })
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })
})

test('the band yields to a survey', async ($, on) => {
  host(on, world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  }))
  await start($)

  const ui = await $.ui.mount({ ...BAND, props: { ...BAND.props, hasSurvey: true }, surface: 'desktop' })
  expect((await ui.findAll({ type: 'Text' })).map(found => found.text)).toEqual(['engine'])
  await ui.unmount()
})

test('a session file the desktop app has not written yet means no title so far', async ($, on) => {
  const w = world('D0: 🧱 Work', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] },
  })
  w.metadata = null
  host(on, w)
  await start($)
  expect(await labels($, 'desktop')).toEqual({ buttons: [], texts: ['engine'] })

  w.metadata = undefined
  await $.session.attach({ surface: 'desktop', clientId: 'desktop:default' })
  expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: REVIEW'], texts: [] })
})

test('a pull request with later commits opens in the browser unless it is ready to merge', async ($, on) => {
  const w = world('', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa', 'bbb', 'ccc'] },
  }, ['commonfabric/labs\tfix\t12'])
  host(on, w)
  for (const state of ['🟠', '🦚', '🪻']) {
    w.title = `D0: ${state} Work`
    w.ran = []
    await start($)

    expect(await labels($, 'desktop')).toEqual({ buttons: ['D0: OPEN PR #12'], texts: [] })
    await press($, 'D0')
    expect(w.ran).toEqual([['open', 'https://github.com/commonfabric/labs/pull/12']])
  }
})
