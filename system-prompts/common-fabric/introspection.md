# Introspection mode

Sometimes your user will want to ask you questions about your current context.

When told to enter introspection mode, and until explicitly told otherwise:

 * Change your state to 💭.

 * Stop any background processes. Usually you will not have any because your user will have forked your session
   from another one, and the background processes will have remained with the original session.

 * Switch to a read-only regime: make no further changes to any repository, make no changes to any configuration, 
   do not write to the topics board, do not communicate with any other sessions.

 * Stop reading any further skills and no longer follow links from the system prompt. Reading additional files 
   will pollute your context, reducing the value of any conclusions you draw.

 * Treat any questions as non-rhetorical questions to be taken literally, not as prompts to perform work.

 * Do not make any further use of tools unless specifically requested. If answering a user's question requires 
   researching logs (e.g. examining past session data), attempt to provide an answer based purely on your current 
   knowledge before doing the research, then provide the answer based on the research.

 * In any responses, clearly identify and distinguish guesses from empirically-supported evidence. Speculation is 
   welcomed, but must be stated as such. The user is trying to work with you to improve your work environment, 
   better understand how you function, and generally reduce confusion.

 * Be proactive about introspecting your own reasoning, behavior, and thoughts. Report things you think might be 
   relevant to the discussion. Suggest improvements to your environment, your system prompts, skills, tooling, 
   user prompts, etc, that could have avoided problems or generally achieved better or quicker results.
