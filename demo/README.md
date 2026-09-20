# demo

A throwaway branch and a [VHS](https://github.com/charmbracelet/vhs) tape for recording the
profile switcher.

```sh
cd demo/sandbox && vhs ../kontor.tape     # writes demo/kontor.gif
```

`sandbox/` exists so the recording never shows a real branch. A directory name in a terminal
recording is a sentence about whoever runs it, and `conf/branches.conf` here declares exactly one
branch called `sandbox` so nothing else can appear.

The tape shows the part worth showing: `use filing` succeeds, `use analysis` is **refused**,
because a local-first branch may reach a hosted model per session but may not have one as its
default.

**Unrecorded so far.** VHS runs the tape and reports success without producing a file on this
machine. Not yet diagnosed; the machine was under heavy memory pressure at the time. The GIF is
gitignored, so committing the tape does not imply one exists.
