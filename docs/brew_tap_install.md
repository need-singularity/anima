# Homebrew tap — `anima` CLI (Y5)

> Status: **formula + docs staged**. The real tap repo
> (`need-singularity/homebrew-anima`) is a separate task — see
> "Creating the tap repo" below.

## TL;DR install

```bash
brew tap need-singularity/anima
brew install anima
```

`brew tap need-singularity/anima` expands (per Homebrew convention) to the
GitHub repo **`need-singularity/homebrew-anima`**. The formula it ships is
`packaging/brew_formula_anima.rb` from this repo, copied to the tap as
`Formula/anima.rb`.

## What gets installed

| Artifact                                 | Destination                                         |
|------------------------------------------|-----------------------------------------------------|
| `bin/anima` (bash dispatcher)            | `#{prefix}/bin/anima`                               |
| `tool/anima_cli/*.hexa`                  | `#{prefix}/share/anima/anima_cli/`                  |
| `tool/anima_cli/man_install.bash`        | `#{prefix}/share/anima/anima_cli/man_install.bash`  |
| `docs/man/anima.1`                       | `#{prefix}/share/man/man1/anima.1`                  |
| `tool/bash/anima-completion.bash`        | `#{prefix}/etc/bash_completion.d/anima`             |
| `tool/zsh/_anima`                        | `#{prefix}/share/zsh/site-functions/_anima`         |
| `tool/fish/anima.fish`                   | `#{prefix}/share/fish/vendor_completions.d/anima.fish` |

`#{prefix}` is `/opt/homebrew` on Apple Silicon, `/usr/local` on Intel
macOS / Linuxbrew.

## Runtime dependencies

- **`bash`** — declared dependency (`depends_on "bash"`).
- **`hexa-lang`** — required at run time to execute the `.hexa` modules,
  but **not yet a brew dependency** because the upstream hexa tap
  (`need-singularity/hexa`) is not public. The formula emits a caveat
  pointing users at the manual install until the tap ships. Once
  published, flip the commented line in `packaging/brew_formula_anima.rb`:
  ```ruby
  depends_on "need-singularity/hexa/hexa-lang"
  ```

## Verification (post-install)

```bash
anima --version               # prints 0.1.0
anima --help                  # prints 15-topic dispatcher banner
man anima                     # opens the installed man page
anima compute status          # end-to-end dispatch smoke
```

Completion smoke (zsh):

```zsh
compinit
anima <TAB>                   # should list: compute weight proposal cert …
```

## Creating the tap repo (operator only)

The tap repo is a thin GitHub repo whose only required content is a
`Formula/` directory. Steps:

1. **Create the repo.** Name must be exactly `homebrew-anima` under the
   `need-singularity` org (Homebrew rewrites `need-singularity/anima`
   → `need-singularity/homebrew-anima`):
   ```bash
   gh repo create need-singularity/homebrew-anima --public \
     --description "Homebrew tap for the anima CLI"
   ```
2. **Stage the formula.**
   ```bash
   git clone git@github.com:need-singularity/homebrew-anima.git
   cd homebrew-anima
   mkdir -p Formula
   cp ../anima/packaging/brew_formula_anima.rb Formula/anima.rb
   ```
3. **Fill in the release sha.** After tagging `v0.1.0` on the main anima
   repo and letting GitHub auto-generate the source tarball:
   ```bash
   curl -sL https://github.com/need-singularity/anima/archive/refs/tags/v0.1.0.tar.gz \
     | shasum -a 256
   # paste the digest into the `sha256 "…"` line of Formula/anima.rb
   ```
4. **Audit + push.**
   ```bash
   brew audit --strict --new-formula Formula/anima.rb
   git add Formula/anima.rb
   git commit -m "anima 0.1.0 (Y5)"
   git push origin main
   ```
5. **Smoke install from a clean host.**
   ```bash
   brew untap need-singularity/anima || true
   brew tap need-singularity/anima
   brew install anima
   brew test anima
   ```

## Updating the formula on new releases

On each `anima` tag bump:

1. Update `version` + `url` + `sha256` in
   `packaging/brew_formula_anima.rb` (source of truth).
2. Copy to `homebrew-anima/Formula/anima.rb` and push.
3. Run `brew audit --strict anima` before tagging the tap commit.

## Selftest (this repo)

```bash
# Ruby syntax check — always works, no brew needed.
ruby -c packaging/brew_formula_anima.rb

# Full audit — requires Homebrew ≥ 4.x on PATH.
brew audit --strict --new-formula packaging/brew_formula_anima.rb
```

The Ruby syntax check is the gate enforced by the Y5 selftest; the
`brew audit` invocation is optional and only runnable on hosts with
Homebrew installed.

## Constraints honoured

- No Python anywhere in the install path (raw#9).
- `man_install.bash` is bash-only; dispatch modules are hexa-only.
- Shell completions covered for bash, zsh, fish (raw#12 — discoverability).
- Formula contains no hardcoded absolute paths outside Homebrew's
  canonical variables (`bin`, `share`, `man1`, `*_completion`) (raw#15).

## See also

- `packaging/brew_formula_anima.rb` — formula source of truth.
- `docs/brew_install.md` — legacy bottle-only formula (N74, CP1 bins).
- `docs/anima_cli_install.md` — non-brew install paths.
- `docs/man/anima.1` — installed man page source.
- `tool/anima_cli/man_install.bash` — man installer helper.
