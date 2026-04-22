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
