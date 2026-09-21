# demo

A throwaway branch for trying the profile switcher without touching a real one.

```sh
cp -R demo/sandbox /tmp/sandbox          # the name matters: the branch is
cd /tmp/sandbox                          # identified by its directory name
export KONTOR_CONF=/path/to/kontor/demo/conf/branches.conf
export KONTOR_PROFILES=/path/to/kontor/demo/conf/profiles.conf
/path/to/kontor/tools/kontor use filing
/path/to/kontor/tools/kontor use analysis   # refused
```

Both variables name a **file**, not the directory. Pointed at a directory they fall back to
`~/.config/kontor/`, and the demo then reports on your real configuration instead.

`sandbox/` exists so that nothing shown here is a real branch. A directory name in a terminal is a
sentence about whoever runs it, and `conf/branches.conf` declares exactly one branch, `sandbox`, so
nothing else can appear.

What to look for: `use filing` succeeds, and `use analysis` is **refused**, because a local-first
branch may reach a hosted model per session but may not have one as its default. The
[README](../README.md) shows the real output.

## Why there is no recording

There was a [VHS](https://github.com/charmbracelet/vhs) tape here, and it never produced a file. The
cause turned out to be a version mismatch, not the tape and not the machine:

- VHS 0.12.0 starts `ttyd` with `-t rendererType canvas`. ttyd 1.7.7 requires `-t key=value` and
  exits at once with `invalid client option`. VHS records nothing and still reports success.
- Rewriting those arguments gets ttyd running and the browser connected. VHS then still writes no
  file and never calls ffmpeg. That second cause was not found.

The tape was removed rather than kept as something that looks like it works. The printed output in
the README is the same thing the recording would have shown.
