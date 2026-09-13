# The fallback

What happens when the subscription runs out. A second agent runner, configured per branch, with a
local model as the default where it matters.

## Which branch gets what

| Branch class | Default model | Web search | Hosted available |
|---|---|---|---|
| local-first | a local model on this machine | no | yes, one deliberate keystroke |
| everything else | a free hosted model | yes, via an MCP search server | — |

The classification lives in the instance config, not here.

🔑 **The default is the protection, not a wall.** In the local-first branches the runner starts on
the local model, so nothing leaves the machine on a prompt typed without thinking. Going online is
one keystroke and the banner says which mode you are in.

⚠️ **This was once a kernel-level seal** — a sandbox profile permitting exactly one network
destination, so a hosted call returned *operation not permitted*. It was removed deliberately, and
the argument is worth keeping because it is easy to get backwards:

> The same material already went to one hosted vendor every day. A seal that blocked a second while
> the first read everything was not protecting the material; it was protecting a vendor's share of
> it.

What survived the argument is the distinction between **accident and intention**. With a hosted
default, the first question is sent before the thought *which model am I on* arrives; noticing
happens on the second prompt, not the first. Local-first removes exactly that and nothing else.

The sandbox profile is kept, unused, in case the decision is revisited.

## Configuration is generated, not hand-written

A script writes the runner's config into every branch from the classification lists, and appends
the config filename to each branch's `.gitignore` as it goes.

📌 **That last part came from a sibling branch noticing a question it should not have to answer.**
The config arrived untracked in its repository, leaving it to decide whether to commit or ignore
it — a decision eleven branches would answer eleven ways. Its reasoning generalises:

> **A distributed file is cheapest when it is clearly documentation (commit it) or clearly
> machinery (ignore it), and expensive when it sits between.**

The manifest is documentation and is committed. The runner config is machinery: an output of a
script that is itself versioned, whose history nobody will ever read, and which in a repository
later shared with collaborators names a personal account.

## The sandbox list is generated, not written twice

The wrapper that decides whether a branch is local-first reads a file the distribution script
writes. It previously carried its own hardcoded list — a second copy of a decision, which is the
shape of every drift in [`lessons.md`](lessons.md).

**It fails closed.** If that list or the profile is missing, the wrapper sandboxes everything rather
than nothing. A missing file must never silently open a hosted route.

## Things that bit us

- **The endpoint needs its version path.** The runner posts to `base_url` + `/chat/completions`; a
  base URL without `/v1` returns `404 page not found`.
- **A context window pinned too large does not fail, it thrashes.** An 8B model pinned to 32K on a
  16 GB machine never loaded and left the machine swapping for a day. `ollama ps` showed nothing;
  the request simply never returned.
- **Disabling default providers disables your own too** unless you give it an explicit model list.
  Auto-discovery alone produces *"default providers are disabled and there are no custom providers
  configured"*, which reads like a config that was ignored.
- **Reasoning models spend the token budget before answering.** With a small `max_tokens` the
  reasoning consumes all of it and `content` comes back **empty** — a successful call that looks
  like a failure. The flag that appears to disable thinking is ignored on the OpenAI-compatible
  endpoint; the budget is the real control.
- **The session database is plaintext inside the repository.** Every message of every session. The
  runner writes its own `.gitignore` for it; do not depend on a vendor's housekeeping for that.
- **macOS has no `timeout`.** Two verification attempts failed for that reason and looked like
  findings.

## Proving the boundary still holds

Re-run after every upgrade of the runner.

1. **Only the expected models are listed.**
2. **A poisoned environment changes nothing** — fake hosted API keys in the environment must not
   make hosted providers appear.
3. **The real test: a deliberately hostile config with a *valid* key**, inside a local-first branch.
   Expect a connection-level refusal. **A `401` would mean the request reached the provider and the
   boundary is broken** — know the difference before you trust the result.
4. **Then the positive control.** The same config in a non-local-first branch must succeed. A
   boundary you have never seen open is an outage, not a boundary.
5. **Confirm the model actually received the repository's rules.** Ask it, without letting it read
   files, what the branch's constitutional rules are. If it cannot answer, the context is being
   truncated and every session so far has run blind.

---
← [README](../README.md) · [Choosing a model](choosing-a-model.md)
