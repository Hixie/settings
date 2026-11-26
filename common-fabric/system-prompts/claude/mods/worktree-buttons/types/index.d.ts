/** What pressing a button does. */
export type WorktreeAction =
  /** Runs a command. */
  | { kind: 'run'; argv: readonly string[] }
  /** Sends the session a message, as if the person had typed it. */
  | { kind: 'say'; text: string }

export type WorktreeButton = {
  /**
   * The worktree identifier, as the session title gives it, or the topic,
   * such as top/1234.
   */
  id: string
  /** The text the band shows for the worktree or topic. */
  label: string
  /** What a press does, or null when the worktree offers nothing to do. */
  action: WorktreeAction | null
  /** Dim buttons drawn beside the first, in order. */
  alternates?: readonly WorktreeAlternate[]
}

export type WorktreeAlternate = { label: string; action: WorktreeAction }

declare module 'claude-code' {
  interface PluginState {
    'worktree-buttons': {
      /** The buttons, or null while they are being worked out. */
      entries: readonly WorktreeButton[] | null
      /** The keys of the buttons whose presses have not finished. */
      pending: readonly string[]
    }
  }
}
