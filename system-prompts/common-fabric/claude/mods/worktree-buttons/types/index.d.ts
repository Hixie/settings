/** What pressing a button does. */
export type WorktreeAction =
  /** Runs a command. */
  | { kind: 'run'; argv: readonly string[] }
  /** Sends the session a message, as if the person had typed it. */
  | { kind: 'say'; text: string }

export type WorktreeButton = {
  /** The worktree identifier, as the session title gives it. */
  id: string
  /** The text the band shows for the worktree. */
  label: string
  /** What a press does, or null when the worktree offers nothing to do. */
  action: WorktreeAction | null
  /** A second button drawn beside the first. */
  alternate?: { label: string; action: WorktreeAction }
}

declare module 'claude-code' {
  interface PluginState {
    'worktree-buttons': { entries: readonly WorktreeButton[] }
  }
}
