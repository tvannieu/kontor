# kontor.tape — the profile switcher in eight seconds.
# Record from inside demo/sandbox:  cd demo/sandbox && vhs ../kontor.tape
# No absolute paths here on purpose: this file is published.
#
# Runs against demo/sandbox and demo/conf, never a real branch: the recording
# must not show a directory name that says anything about whoever runs it.

Output "../kontor.gif"
Set FontSize 20
Set Width 1100
Set Height 620
Set Padding 22
Set Theme "Catppuccin Mocha"
Set TypingSpeed 55ms
Set Shell bash

Hide
Type "export PS1='$ ' KONTOR_CONF=$(cd ../conf && pwd)/branches.conf; clear" Enter
Show

Sleep 700ms
Type "kontor profiles" Enter
Sleep 2800ms

Type "kontor which" Enter
Sleep 2200ms

Type "kontor use filing" Enter
Sleep 2000ms

Type "kontor which" Enter
Sleep 2400ms

# the part that matters: a local-first branch refuses a hosted default
Type "kontor use analysis" Enter
Sleep 4000ms
