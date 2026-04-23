# anima(1) manual page

Standard Unix man page for the `anima` CLI.

## Install (manual)

```sh
cp docs/man/anima.1 /usr/local/share/man/man1/
mandb                      # optional; Homebrew updates whatis index automatically
man anima
```

On macOS with Homebrew, `/usr/local/share/man/man1/` (Intel) or
`/opt/homebrew/share/man/man1/` (Apple Silicon) is already on the default
`MANPATH`. Run `manpath` to confirm.

## Install (wrapper)

Use the helper script:

```sh
tool/anima_cli/man_install.bash --install        # copies into MANPATH
tool/anima_cli/man_install.bash --uninstall      # removes the installed copy
tool/anima_cli/man_install.bash --lint           # runs mandoc -Tlint
```

Set `MAN_PREFIX=/custom/path` to override the install root (default:
`/opt/homebrew/share` on Apple Silicon, `/usr/local/share` elsewhere).

## Verify

```sh
mandoc -Tlint docs/man/anima.1   # lint (should be silent)
man ./docs/man/anima.1           # render without installing
```
