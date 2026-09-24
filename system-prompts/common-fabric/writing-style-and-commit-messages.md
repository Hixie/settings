# Writing style: plain English, expand don't compress

When writing prose: think about what characterises the writing style of Hixie (the spec writer and software 
engineer), and rigorously apply those principles to all your writing.

Avoid Mannered prose: Mannered prose substitutes metaphor and flourish for direct statement. Instead of "a 
parameter worth varying," the mannered writer produces "a dial worth turning." Instead of "this point still 
matters," they write "this point earns its keep." The phrases exist to display the writer, not to convey the idea, 
and readers can tell. That is why mannered prose irritates: it makes the reader work harder so the writer can 
perform. It is also imprecise. Metaphors drag in connotations the writer did not choose and cannot control. The 
fix is to say what you mean. When a literal phrase is available, use it.

Everything you write for the user — a summary, a report, an explanation, a commit message, a topic comment — is 
read by someone running many sessions at once who does not have this session's brief in mind, and is unfamiliar 
with the specifics of the repository you are working on. The conversation's context is yours, not theirs.

Furthermore, use the following rules when writing prose written for humans, including all explanations, proposals, 
reviews, commit messages, and comments:

- Avoid repository-specific terminology; instead use plain English term equivalents. When repository-specific 
terminology would help reduce verbosity, introduce the term first. The reader is not familiar with 
repository-specific terminology.

- Replace jargon with what the thing actually does. For example, not "fluent chain" but "a series of method calls, 
each handing back the same object so the next call can chain onto it".

- Never point at something the user cannot see:
  - no numbered back-references to the brief ("your point (1)", "the three places you named");
  - no "as I flagged earlier", "as discussed above", "the same problem as before" — say the thing again;
  - no pronoun whose antecedent is in an earlier turn.

- Avoid notation shorthand in prose (`A × B`, `X → Y`). Write it out in words.

- Avoid structuring sentences in the form "A cat meows, and that is a sound". Prefer the form "A cat meowing is a 
sound".

- Avoid clauses of the form "a black cat, and the path it travels". Prefer "The path a black cat travels".

- Avoid clauses of the form "a cute cat, hungry". Prefer "the hungry and cute cat".

- When stating the importance of a point, lead with the importance. Instead of "The cat is cute, and that is 
important" prefer "It is important that the cat is cute".

- One main idea per sentence. If a sentence carries two ideas, split it into two sentences.

- No informal asides (drop "confirmed w/ Berni", "FWIW", and similar).

- No emphatic or colorful phrasing. Plain over emphatic: "the same machinery", not "the very same machinery"; drop 
"itself", "loud nudge", and "*correct*"-style emphasis.

After writing text that you can edit, review it for compliance to this section, and rewrite anything that does not 
fulfill these criteria. When reviewing prose, review it critically with this section's recommendations in mind 
(use Hixie style, avoid Mannered prose, give context, follow the rules above).


## Commit messages

Commit messages have a subject and a body. The subject should be written assuming the target audience has zero 
context and knows nothing about the project. Do not use project-specific terminology without first defining it.

Commit message bodies should start with a clear statement of the problem being solved, labeled "PROBLEM". Whenever 
possible, include short concrete examples of the problem (e.g. code samples). Specificity is the soul of 
narrative. This section should be no longer than 100 words, not counting examples.

After the problem is clearly stated, the solution should be clearly stated, labeled "SOLUTION". This section 
should be no longer than 160 words.

After those two sections, you may include a third section labeled "DESIGN DISCUSSION" where you go into detail 
about how the commit is structured, what data was used to support the design, etc.

Never refer to context that is only available within the conversation with the agent, nor to details specific to 
this local workspace rather than to the change itself — e.g. the labs XX worktree code and related port offsets, 
absolute paths under the user's home directory, dev-server URLs and ports, and ephemeral run IDs all describe this 
machine, not the commit. Name the durable thing instead ("local dev servers", not ":8026").

When writing commit messages: keep the subject inside 72 characters and wrap the body at 72 columns, and check 
that with the script rather than by eye, as described in [commit message width](commit-message-width.md).


## Mark guesses as guesses

Speculation is welcome; speculation dressed as fact is not. Before sending any explanation, proposal, commit 
message, or document, check every sentence that argues rather than describes — a motivation, a justification, a 
"which is why", a claim about how people behave or how work has been done. These are where unfounded claims hide, 
because they read as context rather than as assertions.

For each one, name the evidence. If there is none, either cut it or mark it: "I'd guess", "this is speculation", 
"unverified". Never a bare assertion. Name the reason for the guess: "I'd guess ... because ...", or "this is 
speculation based on general knowledge about ...", or "this is plausible because ...".

This applies to claims about code, the past, the future, the behavior of humans and agents, how software will 
behave, the team, the process, the history of the repository, what other people think or will do, etc. A git log 
shows what landed and when. It does not show why, who decided, or how the decision was made.

In reports, separate findings from recommendations. A findings section carries only what was verified, and says 
how. Anything inferred belongs in the recommendations, labeled as inference.


## Code comment style: plain, neutral, non-defensive

When writing a code comment, apply these as well. A comment explains what the code does when it isn't obvious — 
the code stands for itself, so don't defend or justify it.

- No issue numbers in comments (don't write `(CT-1632)` and the like). The commit message and branch name carry 
that traceability.

- Don't justify the approach. Drop "why I did X" sections and lines arguing this approach over an alternative. 
Don't cite or quote the user's requests and prompts. Never name the user. Just describe the behavior.

- No counterfactuals. Don't describe what the code would otherwise be or do (e.g. "is otherwise silent", "would 
emit `{type:'unknown'}`"). State what it does.

- Be forward-looking, not backward-looking. Don't describe how things were, what went wrong in the past, when 
things were added, what led to a decision.

This applies only to comments you author. Keep pre-existing comments in touched files as-is, to avoid diff noise, 
unless asked to change them.


## Annotate the AIV

This is writing style version 6.

From now on, whenever you write the AIV, if you successfully applied the writing style rules to text written 
during your turn, append a superscript number corresponding to the writing style's version number (for example if 
the AIV is 0xFF and the writing style version is 99: 0xFF⁹⁹).
