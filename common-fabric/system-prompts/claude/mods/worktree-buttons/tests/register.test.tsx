import { expect, test } from 'claude-code/testing'
import type { Engine } from 'claude-code/testing'
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
}

type World = {
  title: string
  // The session's metadata file when it is not just the title, or null
  // before the desktop app has written it.
  metadata?: string | null
  // The pull request table, or null when the file does not exist.
  prs: string | null
  checkouts: Record<string, Checkout>
  ran: (readonly string[])[]
  home: string
  // How the commands a press runs fail, if they do.
  pressFails?: 'busy' | 'error'
  toasts: string[]
  runs: number
  // What the session was sent, and why it refuses to take messages, if it does.
  said: string[]
  refusesMessages?: string
}

const LABS_REMOTES = {
  origin: 'git@github.com:hixie/labs.git',
  upstream: 'https://github.com/commonfabric/labs',
}

type Answer = { code: number; stdout?: string; stderr?: string } | { deny: string }

// What the host's commands answer: the pull request table, the commands a
// press runs, and git in the checkouts that exist.
function answer(world: World, argv: readonly string[], cwd: string | undefined): Answer {
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
      const checkout = world.checkouts[cwd ?? '']
      if (checkout === undefined) {
        return { deny: `no such directory: ${cwd}` }
      }
      const remotes = Object.entries(checkout.remotes)
      switch (args[0]) {
        case 'config':
          return remotes.length === 0 ? { code: 1 } : { code: 0, stdout: remotes.map(([name, url]) => `remote.${name}.url ${url}\n`).join('') }
        case 'rev-list': {
          const comparison = `refs/remotes/${'upstream' in checkout.remotes ? 'upstream' : 'origin'}/main`
          expect(args).toEqual(['rev-list', '--reverse', '--topo-order', '--abbrev-commit', 'HEAD', '--not', comparison])
          return !checkout.unfetched
            ? { code: 0, stdout: checkout.commits.map(commit => `${commit}\n`).join('') }
            : { code: 128, stderr: `fatal: bad revision '^${args.at(-1)}'\n` }
        }
        case 'symbolic-ref':
          return checkout.branch === null ? { code: 1 } : { code: 0, stdout: `${checkout.branch}\n` }
      }
    }
  }
  throw new Error(`unexpected command ${argv.join(' ')}`)
}

// Stands in for the host: the environment, the file system (only the
// repository folders exist), the commands the mod runs, and the session's
// prompt.
function host(on: On, world: World) {
  const env: Record<string, string> = {
    HOME: world.home,
    CLAUDE_CODE_ACCOUNT_UUID: 'account',
    CLAUDE_CODE_ORGANIZATION_UUID: 'organization',
    CLAUDE_CODE_HOST_SESSION_ID: 'local_session',
  }
  on('env.get', (_, e) => ({ value: env[e.name] }))
  on('fs.exists', (_, e) => ({
    value: e.path === METADATA.replace(HOME, world.home)
      ? world.metadata !== null
      : ['labs', 'loom', 'web-weaver', 'commonfabric-weaver', 'specs'].some(repo => e.path === `${world.home}/dev/commonfabric/${repo}`),
  }))
  on('prompt.submit', (_, e) => {
    expect(e.origin).toEqual({ kind: 'plugin', name: 'worktree-buttons', asUser: true })
    if (world.refusesMessages !== undefined) {
      return { drop: world.refusesMessages }
    }
    world.said.push(e.text)
    return { text: e.text }
  })
  on('fs.read', (_, e) => {
    expect(e.path).toBe(METADATA.replace(HOME, world.home))
    expect(world.metadata).not.toBeNull()
    return { value: world.metadata ?? JSON.stringify({ sessionId: 'local_session', title: world.title }) }
  })
  on('ui.toast', (_, e) => {
    world.toasts.push(e.text)
    return { value: undefined }
  })
  on('process.spawn', async function* (_, { argv, cwd }) {
    world.runs += 1
    const result = answer(world, argv, cwd)
    if ('deny' in result) {
      return result
    }
    if (result.stdout) {
      yield { stream: 'stdout' as const, text: result.stdout }
    }
    if (result.stderr) {
      yield { stream: 'stderr' as const, text: result.stderr }
    }
    return { value: { code: result.code, signal: null } }
  })
  // The engine's own band, drawn when the mod has nothing to show.
  on('ui.render', ($, e) => {
    const { Text } = $.ui.resolve(e)
    return <Text>engine</Text>
  })
  on('session.start', (_, e) => ({ cwd: e.cwd }))
  on('session.attach', (_, e) => ({ clientId: e.clientId }))
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

  await press($, 'D0 alternate')
  expect(w.said).toEqual(['squash'])
  expect(w.ran).toHaveLength(2)

  w.refusesMessages = 'a Stop hook is blocking'
  await press($, 'D0 alternate')
  expect(w.toasts).toEqual(['D0: SQUASH: a Stop hook is blocking'])
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
  const w = world('D0, D1, 𝛌E3: ✅ Ship it', {
    [`${CF}/labs/D0`]: { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa', 'bbb', 'ccc'] },
    [`${CF}/labs/D1`]: { remotes: LABS_REMOTES, branch: 'two', commits: ['eee', 'fff'] },
    [`${CF}/loom/E3`]: { remotes: { origin: 'git@github.com:commonfabric/loom.git' }, branch: 'fix', commits: ['ddd'] },
  }, ['commonfabric/labs\tfix\t12', 'commonfabric/labs\ttwo\t13', 'commonfabric/loom\tfix\t34'])
  host(on, w)
  await start($)

  for (const surface of SURFACES) {
    // A single new commit has no separate review of each commit.
    expect(await labels($, surface)).toEqual({
      buttons: ['D0: REVIEW TO MERGE (2 new commits, PR #12)', 'EACH COMMIT', 'D1: REVIEW TO MERGE (1 new commit, PR #13)', '𝛌E3: REREVIEW TO MERGE (PR #34)'],
      texts: [],
    })
  }
  // The two buttons of a worktree stay together when the row wraps.
  const ui = await $.ui.mount({ ...BAND, surface: 'desktop' })
  expect((await ui.find({ key: 'D0 group' }))?.children).toHaveLength(2)
  expect((await ui.find({ key: 'D1 group' }))?.children).toHaveLength(1)
  await ui.unmount()
  await press($, 'D0')
  await press($, 'D0 alternate')
  await press($, 'D1')
  await press($, '𝛌E3')
  expect(w.ran).toEqual([
    iterm(`cd ${CF}/labs/D0; c bbb..ccc`),
    iterm(`cd ${CF}/labs/D0; c bbb..ccc --separate`),
    iterm(`cd ${CF}/labs/D1; c fff..fff`),
    iterm(`cd ${CF}/loom/E3; c`),
  ])
})

test('a pull request opens in the browser in any state but ✅', async ($, on) => {
  const w = world('', {
    [`${CF}/commonfabric-weaver/A1`]: {
      remotes: { origin: 'https://github.com/CommonFabric/commonfabric-weaver.git' },
      branch: 'feature',
      commits: ['aaa'],
    },
  }, ['commonfabric/commonfabric-weaver\tfeature\t7', 'commonfabric/commonfabric-weaver\tfeature\t9'])
  host(on, w)
  for (const state of ['🪻', '🦚', '🧱']) {
    w.title = `ωA1: ${state} Weaver work`
    w.ran = []
    await start($)

    expect(await labels($, 'desktop')).toEqual({ buttons: ['ωA1: OPEN PR #9'], texts: [] })
    await press($, 'ωA1')
    expect(w.ran).toEqual([['open', 'https://github.com/commonfabric/commonfabric-weaver/pull/9']])
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
  for (const title of ['🧱 Fix: a bug in the parser', 'Untitled session', '💬 Question']) {
    w.title = title
    await start($)

    expect(await labels($, 'desktop')).toEqual({ buttons: [], texts: ['engine'] })
  }
})

test('a worktree that is not a git checkout says so', async ($, on) => {
  host(on, world('ZZ: 🧱 Gone', {}))
  await start($)

  const { buttons, texts } = await labels($, 'desktop')
  expect(buttons).toEqual([])
  expect(texts).toEqual([expect.stringMatching(/^ZZ: ERROR: .*no such directory/u)])
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
    '𝛌E3': `${CF}/loom/E3`,
    lf2: `${CF}/loom/F2`,
    'ωA1': `${CF}/commonfabric-weaver/A1`,
    wb2: `${CF}/commonfabric-weaver/B2`,
    INFRA2: `${CF}/infra/2`,
    deno5: `${HOME}/dev/denoland/5`,
    cliffy: `${HOME}/dev/cliffy/root`,
    'cfs-K1': `${CF}/loom/K1`,
    'weaver-C3': `${CF}/commonfabric-weaver/C3`,
    web: `${CF}/web-weaver/root`,
    'web-A1': `${CF}/web-weaver/A1`,
    'gvisor-82': `${CF}/gvisor/82`,
    labs: `${CF}/labs/root`,
    specs: `${CF}/specs/root`,
    L3: `${CF}/labs/L3`,
    d0: `${CF}/labs/D0`,
    contraptions: `${HOME}/dev/contraptions`,
  }
  const ids = Object.keys(paths)
  host(on, world(`${ids.join(', ')}, D0X, D0: 🧱 Everything`, Object.fromEntries(
    Object.values(paths).map(path => [path, { remotes: LABS_REMOTES, branch: 'fix', commits: ['aaa'] }]),
  )))
  await start($)

  // D0X is not an identifier, and D0 is the folder d0 already named.
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
