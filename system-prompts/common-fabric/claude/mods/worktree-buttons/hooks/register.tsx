import type { EngineInterface, Register } from 'claude-code'

import type { WorktreeAction, WorktreeButton } from '../types'

// The session title has the shape "WORKTREES: STATE SUMMARY", where WORKTREES
// is a comma-separated list of worktree identifiers and STATE is an emoji. For
// each worktree, the band above the prompt shows a button labeled with the
// identifier and what pressing the button does, and sometimes a second button
// beside it; the README lists the labels.

const ENTRIES = { plugin: 'worktree-buttons', key: 'entries' } as const

type PullRequest = { repo: string; branch: string; number: number }

// The exit status of lockf -n when the file does not exist (EX_UNAVAILABLE).
const LOCKF_MISSING = 69

// Runs a command to its end, with no time limit: a command may wait on the
// pull request table's lock, or on the person allowing iterm-run's first
// Apple Event to iTerm2.
async function run($: EngineInterface, argv: readonly string[], cwd?: string) {
  const child = $.process.spawn(cwd === undefined ? { argv } : { argv, cwd })
  let stdout = ''
  let stderr = ''
  for await (const { stream, text } of child) {
    if (stream === 'stdout') {
      stdout += text
    } else {
      stderr += text
    }
  }
  const { code, signal } = await child.result
  return { code, signal, stdout: stdout.replace(/\n$/, ''), stderr: stderr.trim() }
}

async function mustRun($: EngineInterface, argv: readonly string[], cwd?: string) {
  const { code, signal, stdout, stderr } = await run($, argv, cwd)
  if (code !== 0) {
    throw new Error(`${argv.slice(0, 2).join(' ')}: ${stderr || signal || `exit ${code}`}`)
  }
  return stdout
}

function message(error: unknown) {
  return error instanceof Error ? error.message : String(error)
}

function lines(text: string) {
  return text === '' ? [] : text.split('\n')
}

async function sessionTitle($: EngineInterface, home: string) {
  const account = await $.env.get('CLAUDE_CODE_ACCOUNT_UUID')
  const organization = await $.env.get('CLAUDE_CODE_ORGANIZATION_UUID')
  const session = await $.env.get('CLAUDE_CODE_HOST_SESSION_ID')
  if (account === undefined || organization === undefined || session === undefined) {
    return null
  }
  // The desktop app writes this file shortly after the session starts; until
  // then, the title is not known.
  const metadata = `${home}/Library/Application Support/Claude/claude-code-sessions/${account}/${organization}/${session}.json`
  if (!(await $.fs.exists(metadata))) {
    return null
  }
  const { title } = JSON.parse(await $.fs.read(metadata))
  return typeof title === 'string' ? title : null
}

const PREFIXED_REPOSITORIES: readonly [RegExp, string][] = [
  [/^(?:𝛌|l(?=.{0,2}$))/u, 'commonfabric/loom'],
  [/^(?:ω|w(?=.{0,2}$))/u, 'commonfabric/commonfabric-weaver'],
  [/^INFRA/u, 'commonfabric/infra'],
  [/^deno/u, 'denoland'],
  [/^cliffy/u, 'cliffy'],
]

const SHORT_NAMES: Readonly<Record<string, string>> = {
  cfs: 'loom',
  weaver: 'commonfabric-weaver',
  web: 'web-weaver',
}

// The directory a worktree identifier names, following the same rules as
// ~/bin/l, or null when the text is not a worktree identifier.
async function worktreePath($: EngineInterface, home: string, id: string) {
  if (['contraptions', 'settings', 'usable-git'].includes(id)) {
    return `${home}/dev/${id}`
  }
  const commonfabric = `${home}/dev/commonfabric`
  let root: string
  let code: string
  const prefixed = PREFIXED_REPOSITORIES.find(([pattern]) => pattern.test(id))
  if (id === 'web') {
    root = `${commonfabric}/web-weaver`
    code = ''
  } else if (prefixed !== undefined) {
    const [pattern, repository] = prefixed
    root = `${home}/dev/${repository}`
    code = id.replace(pattern, '')
  } else {
    let repository = id
    code = ''
    if (id.includes('-') && !(await $.fs.exists(`${commonfabric}/${id}`))) {
      repository = id.slice(0, id.lastIndexOf('-'))
      code = id.slice(id.lastIndexOf('-') + 1)
    }
    repository = SHORT_NAMES[repository] ?? repository
    if (code === '' && !(await $.fs.exists(`${commonfabric}/${repository}`))) {
      repository = 'labs'
      code = id
    }
    root = `${commonfabric}/${repository}`
  }
  if (code === '') {
    return `${root}/root`
  }
  const upper = code.toUpperCase()
  return /^[0-9A-Z]{1,2}$/u.test(upper) ? `${root}/${upper}` : null
}

// The pull requests github-hookbar lists. Lines that are not about a pull
// request are skipped, as github-hookbar itself skips them.
async function pullRequests($: EngineInterface, home: string): Promise<readonly PullRequest[]> {
  // lockf holds a flock(2) lock on the file while cat reads it, so a rewrite
  // in progress is never seen half done. Without -k, lockf would delete the
  // file afterwards; -n makes it fail rather than create a missing file.
  const path = `${home}/.cache/github-prs.tsv`
  const argv = ['lockf', '-kn', path, 'cat', path]
  const { code, signal, stdout, stderr } = await run($, argv)
  if (code === LOCKF_MISSING) {
    return []
  }
  if (code !== 0) {
    throw new Error(stderr || `lockf: ${signal ?? `exit ${code}`}`)
  }
  return lines(stdout).flatMap(line => {
    const [repo = '', branch = '', number = '', ...rest] = line.split('\t')
    const isPullRequest = repo !== '' && branch !== '' && /^0*[1-9][0-9]*$/u.test(number) && rest.length === 0
    return isPullRequest ? [{ repo, branch, number: Number(number) }] : []
  })
}

function shellWord(text: string) {
  return /^[\w./-]+$/u.test(text) ? text : `'${text.replaceAll("'", `'\\''`)}'`
}

async function inspect(
  $: EngineInterface,
  id: string,
  path: string,
  state: string,
  prs: readonly PullRequest[],
  main: string,
  itermRun: string,
): Promise<WorktreeButton> {
  // Each line is "remote.NAME.url URL".
  const urls = new Map(
    lines((await run($, ['git', 'config', '--get-regexp', '^remote\\..*\\.url$'], path)).stdout).map(line => {
      const space = line.indexOf(' ')
      return [line.slice(0, space), line.slice(space + 1)]
    }),
  )
  const remote = urls.has('remote.upstream.url') ? 'upstream' : 'origin'
  const comparison = `refs/remotes/${remote}/${main}`
  // Oldest first, so that commits[0] is commit 1.
  const commits = lines(await mustRun($, ['git', 'rev-list', '--reverse', '--topo-order', '--abbrev-commit', 'HEAD', '--not', comparison], path))
  const branch = await run($, ['git', 'symbolic-ref', '--quiet', '--short', 'HEAD'], path)
  // The remote's GitHub repository, as owner/name.
  const url = urls.get(`remote.${remote}.url`) ?? ''
  const repository = /^(?:.*[@/])?github\.com[:/]([^/]+\/[^/]+?)(?:\.git)?\/?$/u.exec(url)?.[1]?.toLowerCase()
  const pr = branch.code !== 0
    ? undefined
    : prs
      .filter(row => row.branch === branch.stdout && row.repo.toLowerCase() === repository)
      .reduce<PullRequest | undefined>((newest, row) => (newest === undefined || row.number > newest.number ? row : newest), undefined)

  const n = commits.length
  const inTerminal = (command: string): WorktreeAction => ({ kind: 'run', argv: [itermRun, `cd ${shellWord(path)}; ${command}`] })
  const button = (label: string, action: WorktreeAction): WorktreeButton => ({ id, label: `${id}: ${label}`, action })
  const terminal = (label: string, command: string) => button(label, inTerminal(command))
  // A worktree with no commits of its own offers to open it, whatever pull
  // request is listed for its branch.
  if (n === 0) {
    return terminal('OPEN WORKTREE', 'l')
  }
  // Without a pull request, SQUASH tells the session's agent to squash the
  // branch's commits.
  if (pr === undefined) {
    const review = terminal(n > 1 ? `REVIEW (${n} commits)` : 'REVIEW', 'c --separate')
    return n > 1 ? { ...review, alternate: { label: 'SQUASH', action: { kind: 'say', text: 'squash' } } } : review
  }
  if (!state.startsWith('✅')) {
    return button(`OPEN PR #${pr.number}`, { kind: 'run', argv: ['open', `https://github.com/${pr.repo}/pull/${pr.number}`] })
  }
  if (n === 1) {
    return terminal(`REREVIEW TO MERGE (PR #${pr.number})`, 'c')
  }
  // The commits after the oldest one are the new ones to review, together, or
  // one at a time when there is more than one.
  const added = n - 1
  const range = `c ${commits[1]}..${commits[n - 1]}`
  const review = terminal(`REVIEW TO MERGE (${added} new ${added === 1 ? 'commit' : 'commits'}, PR #${pr.number})`, range)
  if (added === 1) {
    return review
  }
  return { ...review, alternate: { label: 'EACH COMMIT', action: inTerminal(`${range} --separate`) } }
}

async function compute($: EngineInterface): Promise<readonly WorktreeButton[]> {
  const home = await $.env.get('HOME')
  if (home === undefined) {
    throw new Error('HOME is not set')
  }
  const title = await sessionTitle($, home)
  const separator = title?.indexOf(': ') ?? -1
  // The state emoji follows the list; a title like "PR: fix flake" has none.
  if (title === null || separator < 0 || /^[\p{L}\p{N}]/u.test(title.slice(separator + 2))) {
    return []
  }
  const state = title.slice(separator + 2)
  const found = (
    await Promise.all(
      title.slice(0, separator).split(',').map(async text => {
        const id = text.trim()
        const path = id === '' ? null : await worktreePath($, home, id)
        return path === null ? [] : [{ id, path }]
      }),
    )
  ).flat()
  const worktrees = found.filter(({ path }, index) => found.findIndex(other => other.path === path) === index)
  if (worktrees.length === 0) {
    return []
  }
  const prs = await pullRequests($, home)
  const main = (await $.env.get('MAIN')) ?? 'main'
  // Runs a command in the shell of iTerm2's frontmost session, only if that
  // shell is idle at an empty prompt; it prints "busy" otherwise.
  const itermRun = `${home}/dev/contraptions/iterm-run/iterm-run`
  return Promise.all(
    worktrees.map(async ({ id, path }) => {
      try {
        return await inspect($, id, path, state, prs, main, itermRun)
      } catch (error) {
        return { id, label: `${id}: ERROR: ${message(error)}`, action: null }
      }
    }),
  )
}

let generation = 0

async function refresh($: EngineInterface) {
  generation += 1
  const mine = generation
  let next: readonly WorktreeButton[]
  try {
    next = await compute($)
  } catch (error) {
    next = [{ id: 'error', label: `worktree-buttons: ${message(error)}`, action: null }]
  }
  if (mine === generation) {
    await $.state.set(ENTRIES, next)
  }
}

// Does what the button showed when it was drawn, and says why when that
// fails, such as iterm-run finding the shell busy.
async function press($: EngineInterface, label: string, action: WorktreeAction) {
  try {
    if (action.kind === 'say') {
      const { drop } = await $.prompt.submit({ text: action.text, asUser: true })
      if (drop !== undefined) {
        $.ui.toast(`${label}: ${drop}`)
      }
    } else {
      const { code, signal, stdout, stderr } = await run($, action.argv)
      if (code !== 0) {
        $.ui.toast(`${label}: ${stderr || stdout || signal || `exit ${code}`}`)
      }
    }
  } catch (error) {
    $.ui.toast(`${label}: ${message(error)}`)
  }
  await refresh($)
}

export const register: Register = on => {
  // Each of these may change the title, the branches, or what the band can
  // show, so the buttons are worked out again once the event is done.
  on('session.start', ($, e, next) => next(e).finally(() => void refresh($)))
  on('session.attach', ($, e, next) => next(e).finally(() => void refresh($)))
  on('turn.complete', ($, e, next) => next(e).finally(() => void refresh($)))
  on('tool.call', { tool: 'mcp__ccd_session_mgmt__set_session_title' }, ($, e, next) =>
    next(e).finally(() => void refresh($)))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { value: shown = [] } = await $.state.get(ENTRIES)
    if (e.props.hasSurvey || shown.length === 0) {
      return next(e)
    }
    const { Box, Button, Text } = $.ui.resolve(e)
    return (
      <Box flexDirection="row" flexWrap="wrap" gap={1}>
        {shown.map(({ id, label, action, alternate }) =>
          action === null
            ? <Text dimColor>{label}</Text>
            : (
              <Box key={`${id} group`} flexDirection="row" gap={1}>
                <Button key={id} label={label} onPress={() => void press($, label, action)} />
                {alternate === undefined
                  ? []
                  : [
                    <Button
                      key={`${id} alternate`}
                      label={alternate.label}
                      dimColor
                      onPress={() => void press($, `${id}: ${alternate.label}`, alternate.action)}
                    />,
                  ]}
              </Box>
            ),
        )}
      </Box>
    )
  })
}
