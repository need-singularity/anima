# anima CLI 전역 install 가이드

## 1. PATH — 이미 완료
`~/.hx/bin/anima` shim 이 `/Users/ghost/core/anima/bin/anima` 로 리다이렉트.
`~/.hx/bin/` 은 `$PATH` 에 이미 있음 → `anima` 아무 디렉토리에서 실행 가능.

backup: `~/.hx/bin/anima.old.20260423` (이전 launch.hexa shim)

## 2. zsh completion
```bash
# 방법 A — 사용자 ~/.zsh/completions 디렉토리
mkdir -p ~/.zsh/completions
cp /Users/ghost/core/anima/tool/zsh/_anima ~/.zsh/completions/
# ~/.zshrc 에 추가 (1회만):
echo 'fpath=(~/.zsh/completions $fpath)' >> ~/.zshrc
echo 'autoload -U compinit && compinit' >> ~/.zshrc
source ~/.zshrc
```

```bash
# 방법 B — homebrew site-functions (brew 사용자)
cp /Users/ghost/core/anima/tool/zsh/_anima $(brew --prefix)/share/zsh/site-functions/
autoload -U compinit && compinit
```

## 2b. bash completion
POSIX bash (bash 3.2+, macOS default 호환). 9 topic + 47 subcmd + context-specific flag 완성.
```bash
# 현재 세션
source /Users/ghost/core/anima/tool/bash/anima-completion.bash

# 영구 (~/.bashrc 에 1회 append)
cat >> ~/.bashrc <<EOF
source /Users/ghost/core/anima/tool/bash/anima-completion.bash
EOF
```

검증:
```bash
source /Users/ghost/core/anima/tool/bash/anima-completion.bash
complete -p anima     # → complete -F _anima_completion anima
anima <TAB>           # 10 topics (compute weight proposal cert roadmap serve paradigm inbox cost status)
anima compute <TAB>   # 8 subcmds (status start stop watch cost recover ingest preflight)
anima proposal <TAB>  # 8 subcmds (review approve reject implement archive dashboard cluster cycle)
```

## 2c. fish completion
fish 3+ 표준 completion (9 topic + 39 subcmd, context-aware). fish 는 `~/.config/fish/completions/*.fish` 를 자동 로드.
```bash
cp /Users/ghost/core/anima/tool/fish/anima.fish ~/.config/fish/completions/
# 또는 fish 재시작 (exec fish) — 새 prompt 에서 즉시 활성
```

검증:
```fish
complete -c anima                      # 55 rules (10 topic + 39 subcmd + 6 flag)
fish -c 'complete -c anima' | wc -l    # subshell selftest
anima <TAB>                            # 10 topics
anima compute <TAB>                    # 8 subcmds
```

## 3. 검증
```bash
cd /tmp
anima --version    # "anima 0.1.0"
anima sta<TAB>     # completes to "status"
anima compute <TAB>  # shows 8 subcmds (status start stop watch cost recover ingest preflight)
```

## 4. Rollback (원래 launch.hexa 복귀 시)
```bash
cp ~/.hx/bin/anima.old.20260423 ~/.hx/bin/anima
```
