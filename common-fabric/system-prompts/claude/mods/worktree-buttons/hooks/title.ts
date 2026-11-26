// A session title has the shape "WORKTREES: STATE SUMMARY", where WORKTREES
// is a comma-separated list of worktree identifiers and STATE is an emoji, or
// the shape "STATE SUMMARY" when no worktree is listed.

// One emoji, with any variation selectors, skin tone modifiers, and further
// emoji joined to it by U+200D ZERO WIDTH JOINER.
const EMOJI = '\\p{Extended_Pictographic}(?:[\\u{FE0F}\\u{1F3FB}-\\u{1F3FF}]|\\u{200D}\\p{Extended_Pictographic})*'
const LEADING_EMOJI = new RegExp(`^${EMOJI}`, 'u')
const EVERY_EMOJI = new RegExp(EMOJI, 'gu')

// Emoji such as ⏸️ may be written with or without U+FE0F VARIATION
// SELECTOR-16, so emoji are compared without it.
function plain(emoji: string) {
  return emoji.replaceAll('\u{FE0F}', '')
}

// The whole emoji in a text, such as a sidebar section's name, without
// variation selectors.
export function emojiIn(text: string) {
  return (text.match(EVERY_EMOJI) ?? []).map(plain)
}

// The worktree list (empty when there is none) and the state emoji, without
// variation selectors, of a title; or null when the title has no state.
export function parseTitle(title: string) {
  const leading = LEADING_EMOJI.exec(title)
  if (leading !== null) {
    return { worktrees: '', state: plain(leading[0]) }
  }
  const separator = title.indexOf(': ')
  const state = separator < 0 ? null : LEADING_EMOJI.exec(title.slice(separator + 2))
  return state === null ? null : { worktrees: title.slice(0, separator), state: plain(state[0]) }
}
