# CLI Completion Setup (ROI #78)

zsh tab-completion for `hexa` and `airgenome` CLIs.

## Files

- `shared/completions/_hexa.zsh` — completes hexa subcommands (run/parse/build/test/bench/batch/...).
- `shared/completions/_airgenome.zsh` — completes airgenome subcommands + host aliases for `offload`.

## One-time install

```sh
# 1. Create a per-user completions dir (skip if it exists)
mkdir -p ~/.zsh/completions

# 2. Symlink the anima-shipped completion files
ln -sf /Users/ghost/core/anima/shared/completions/_hexa.zsh \
       ~/.zsh/completions/_hexa
ln -sf /Users/ghost/core/anima/shared/completions/_airgenome.zsh \
       ~/.zsh/completions/_airgenome

# 3. Append to ~/.zshrc (idempotent: check first)
grep -q '~/.zsh/completions' ~/.zshrc || cat >> ~/.zshrc <<'EOF'

# anima CLI completions (ROI #78)
fpath=(~/.zsh/completions $fpath)
autoload -U compinit && compinit
EOF

# 4. Reload
source ~/.zshrc
```

## Verify

```sh
hexa <TAB>       # → run / parse / build / test / bench / batch / ...
airgenome <TAB>  # → init / stop / status / offload / list / logs / ...
airgenome offload <TAB>  # → ubu1 / ubu2 / htz / mac / ubu
```

## Updating

The completion files are tracked under `shared/completions/` in this repo. After a `git pull`, completions are picked up automatically (the symlinks resolve to the repo paths). No re-install needed.

## Troubleshooting

- If completion does not work, ensure `compinit` is running AFTER `fpath` is updated.
- Run `compaudit` and fix insecure directories with `compaudit | xargs chmod g-w`.
- For `bash`, this directory does not yet ship completions — open ROI #78b if needed.
