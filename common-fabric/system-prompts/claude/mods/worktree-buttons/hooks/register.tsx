import type { EngineInterface, Register } from 'claude-code'

import type { WorktreeAction, WorktreeAlternate, WorktreeButton } from '../types'
import { message } from './message.js'
import { hostSession, sort, sortAfter } from './sort-session.js'
import { parseTitle } from './title.js'

// The session title has the shape "WORKTREES: STATE SUMMARY", where WORKTREES
// is a comma-separated list of worktree identifiers and STATE is an emoji. For
// each worktree, the band above the prompt shows a button labeled with the
// identifier and what pressing the button does, and sometimes dim buttons
// beside it; the README lists the labels. While the buttons are being worked
// out, the band shows a spinner in their place.

const ENTRIES = { plugin: 'worktree-buttons', key: 'entries' } as const
const PENDING = { plugin: 'worktree-buttons', key: 'pending' } as const

type PullRequest = { repo: string; branch: string; number: number }

// The exit status of lockf -n when the file does not exist (EX_UNAVAILABLE).
const LOCKF_MISSING = 69

// Runs a command to its end, with no time limit: a command may wait on the
// pull request table's lock, or on the person allowing iterm-run's first
// Apple Event to iTerm2. A command runs in `/` unless it is given a folder, so
// it does not depend on the session's working directory, which may be a
// worktree that has since been deleted.
async function run($: EngineInterface, argv: readonly string[], cwd = '/') {
  const child = $.process.spawn({ argv, cwd })
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

function failure(argv: readonly string[], { code, signal, stderr }: Awaited<ReturnType<typeof run>>) {
  return new Error(`${argv.slice(0, 2).join(' ')}: ${stderr || signal || `exit ${code}`}`)
}

async function mustRun($: EngineInterface, argv: readonly string[], cwd: string) {
  const result = await run($, argv, cwd)
  if (result.code !== 0) {
    throw failure(argv, result)
  }
  return result.stdout
}

function lines(text: string) {
  return text === '' ? [] : text.split('\n')
}

async function sessionTitle($: EngineInterface, home: string) {
  const account = await $.env.get('CLAUDE_CODE_ACCOUNT_UUID')
  const organization = await $.env.get('CLAUDE_CODE_ORGANIZATION_UUID')
  const session = await hostSession($)
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
  [/^ℂ/u, 'commonfabric/cfs'],
  [/^ω/u, 'commonfabric/weaver'],
  [/^INFRA/u, 'commonfabric/infra'],
  [/^deno/u, 'denoland'],
  [/^cliffy/u, 'cliffy'],
]

// Other names of repositories. The lowercase letters among them also mark a
// worktree when followed by its code, as in "c1" for cfs worktree 1.
const OTHER_NAMES: ReadonlyMap<string, string> = new Map([
  ['c', 'cfs'],
  ['w', 'weaver'],
  ['commonfabric-weaver', 'weaver'],
  ['web', 'web-weaver'],
])

// How an identifier that has no mark at its start splits into a repository
// and a code, or null when it does not split. Repository names such as
// web-weaver contain hyphens, so only an identifier that is not itself a
// repository name is split, either at its last hyphen, or after a lowercase
// c or w followed by a code. The volume ignores case, so only an exact
// match among the repositories' names tells "crm", a repository, from "cRM",
// cfs worktree RM.
async function split($: EngineInterface, commonfabric: string, id: string) {
  if (OTHER_NAMES.has(id)) {
    return null
  }
  const hyphenated = /^(.*)-(.*)$/u.exec(id)
  if (hyphenated !== null) {
    return (await $.fs.exists(`${commonfabric}/${id}`)) ? null : hyphenated
  }
  const marked = /^([cw])(.{1,2})$/u.exec(id)
  if (marked !== null && (await $.fs.list(commonfabric)).some(({ name }) => name === id)) {
    return null
  }
  return marked
}

// The directory a worktree identifier names, following the same rules as
// ~/bin/l, or null when the text is not a worktree identifier.
async function worktreePath($: EngineInterface, home: string, id: string) {
  if (['contraptions', 'settings', 'usable-git'].includes(id)) {
    return `${home}/dev/${id}`
  }
  const commonfabric = `${home}/dev/commonfabric`
  if (['dogfood', 'fishfood'].includes(id)) {
    return `${commonfabric}/${id}`
  }
  let root: string
  let code: string
  const prefixed = PREFIXED_REPOSITORIES.find(([pattern]) => pattern.test(id))
  if (prefixed !== undefined) {
    const [pattern, repository] = prefixed
    root = `${home}/dev/${repository}`
    code = id.replace(pattern, '')
  } else {
    const parts = await split($, commonfabric, id)
    const named = parts?.[1] ?? id
    let repository = OTHER_NAMES.get(named) ?? named
    code = parts?.[2] ?? ''
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
  const inTerminal = (command: string): WorktreeAction => ({ kind: 'run', argv: [itermRun, `cd ${shellWord(path)}; ${command}`] })
  const button = (label: string, action: WorktreeAction): WorktreeButton => ({ id, label: `${id}: ${label}`, action })
  const terminal = (label: string, command: string) => button(label, inTerminal(command))
  // A folder that is not a git checkout, such as the one that holds the
  // dogfood clones, has no commits of its own. A folder that does not exist,
  // such as a deleted worktree's, offers nothing.
  if (!(await $.fs.exists(`${path}/.git`))) {
    if (!(await $.fs.exists(path))) {
      return { id, label: `${id}: FOLDER MISSING`, action: null }
    }
    return terminal('OPEN WORKTREE', 'l')
  }
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
  // A worktree with no commits of its own offers to open it, whatever pull
  // request is listed for its branch.
  if (n === 0) {
    return terminal('OPEN WORKTREE', 'l')
  }
  // merge-tree exits with status 1, printing nothing, when merging the
  // branch's commits into the main branch would conflict. REBASE then tells
  // the session's agent to rebase the branch. It also exits with status 1,
  // with a message, when it cannot merge a revision at all.
  const mergeArgv = ['git', 'merge-tree', '--write-tree', '--quiet', comparison, 'HEAD']
  const merge = await run($, mergeArgv, path)
  const conflicts = merge.code === 1 && merge.stderr === ''
  if (merge.code !== 0 && !conflicts) {
    throw failure(mergeArgv, merge)
  }
  const offer = (label: string, action: WorktreeAction, ...alternates: WorktreeAlternate[]): WorktreeButton => ({
    ...button(label, action),
    alternates: conflicts ? [...alternates, { label: 'REBASE', action: { kind: 'say', text: 'rebase' } }] : alternates,
  })
  // Without a pull request, SQUASH tells the session's agent to squash the
  // branch's commits.
  if (pr === undefined) {
    const review = inTerminal('c --separate')
    return n > 1
      ? offer(`REVIEW (${n} commits)`, review, { label: 'SQUASH', action: { kind: 'say', text: 'squash' } })
      : offer('REVIEW', review)
  }
  if (!state.startsWith('✅')) {
    return offer(`OPEN PR #${pr.number}`, { kind: 'run', argv: ['open', `https://github.com/${pr.repo}/pull/${pr.number}`] })
  }
  if (n === 1) {
    return offer(`REREVIEW TO MERGE (PR #${pr.number})`, inTerminal('c'))
  }
  // The commits after the oldest one are the new ones to review, together, or
  // one at a time when there is more than one.
  const added = n - 1
  const range = `c ${commits[1]}..${commits[n - 1]}`
  const label = `REVIEW TO MERGE (${added} new ${added === 1 ? 'commit' : 'commits'}, PR #${pr.number})`
  return added === 1
    ? offer(label, inTerminal(range))
    : offer(label, inTerminal(range), { label: 'EACH COMMIT', action: inTerminal(`${range} --separate`) })
}

// Calls checking once the title is known to name worktrees, before the slower
// work of inspecting them.
async function compute($: EngineInterface, checking: () => Promise<void>): Promise<readonly WorktreeButton[]> {
  const home = await $.env.get('HOME')
  if (home === undefined) {
    throw new Error('HOME is not set')
  }
  const title = await sessionTitle($, home)
  const parsed = title === null ? null : parseTitle(title)
  if (parsed === null || parsed.worktrees === '') {
    return []
  }
  const { state } = parsed
  const found = (
    await Promise.all(
      parsed.worktrees.split(',').map(async text => {
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
  await checking()
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
  // Only the latest refresh changes what the band shows.
  const show = async (entries: readonly WorktreeButton[] | null) => {
    if (mine === generation) {
      await $.state.set(ENTRIES, entries)
    }
  }
  let next: readonly WorktreeButton[]
  try {
    next = await compute($, () => show(null))
  } catch (error) {
    next = [{ id: 'error', label: `worktree-buttons: ${message(error)}`, action: null }]
  }
  await show(next)
}

const pending = new Set<string>()

// What the band says in place of a button whose press has not finished. A
// message waits until the session is idle.
function progress(action: WorktreeAction, isWorking: boolean) {
  if (action.kind === 'run') {
    return 'running'
  }
  return isWorking ? 'sent when this turn ends' : 'sending'
}

// Does what the button showed when it was drawn, and says why when that
// fails, such as iterm-run finding the shell busy. Until the press finishes,
// the band shows its progress in place of the button.
async function press($: EngineInterface, key: string, label: string, action: WorktreeAction) {
  pending.add(key)
  try {
    await $.state.set(PENDING, [...pending])
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
  pending.delete(key)
  await $.state.set(PENDING, [...pending])
  await refresh($)
}

export const register: Register = on => {
  // Each of these may change the title, the branches, or what the band can
  // show, so the buttons are worked out again once the event is done. A
  // session is also sorted into the sidebar section for its state when it
  // starts, and when a call that sets its title or moves it to the top level
  // of the sidebar succeeds.
  on('session.start', ($, e, next) =>
    next(e).finally(() => {
      void refresh($)
      sort($)
    }))
  on('session.attach', ($, e, next) => next(e).finally(() => void refresh($)))
  on('turn.complete', ($, e, next) => next(e).finally(() => void refresh($)))
  on('tool.call', { tool: 'mcp__ccd_session_mgmt__set_session_title' }, ($, e, next) =>
    next(e)
      .then(result => sortAfter($, e.session_id, result))
      .finally(() => void refresh($)))
  on('tool.call', { tool: 'mcp__ccd_session_mgmt__detach_session' }, ($, e, next) =>
    next(e).then(result => sortAfter($, e.session_id, result)))

  on('ui.render', { component: 'AbovePrompt' }, async ($, e, next) => {
    const { value: shown = [] } = await $.state.get(ENTRIES)
    if (e.props.hasSurvey || (shown !== null && shown.length === 0)) {
      return next(e)
    }
    const { Box, Button, Progress, Text } = $.ui.resolve(e)
    if (shown === null) {
      return <Progress label="Checking worktrees" />
    }
    const { value: inFlight = [] } = await $.state.get(PENDING)
    const control = (key: string, label: string, toast: string, action: WorktreeAction, dimColor: boolean) =>
      inFlight.includes(key)
        ? <Text key={key} dimColor>{`${label} (${progress(action, e.props.isWorking)})`}</Text>
        : <Button key={key} label={label} dimColor={dimColor} onPress={() => void press($, key, toast, action)} />
    return (
      <Box flexDirection="row" flexWrap="wrap" gap={1}>
        {shown.map(({ id, label, action, alternates = [] }) =>
          action === null
            ? <Text key={id} dimColor>{label}</Text>
            : (
              <Box key={`${id} group`} flexDirection="row" gap={1}>
                {control(id, label, label, action, false)}
                {alternates.map(alternate =>
                  control(`${id} ${alternate.label}`, alternate.label, `${id}: ${alternate.label}`, alternate.action, true))}
              </Box>
            ),
        )}
      </Box>
    )
  })
}
