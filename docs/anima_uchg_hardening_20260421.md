# anima .own + .roadmap uchg Hardening Ceremony

**date**: 2026-04-21
**operator**: dancinlife (nerve011235@gmail.com)
**context**: 6-SSOT cross-consistency gap closure (commit `c7edd27b`).
anima-side `.own` and `.roadmap` were unlocked while the other 5 SSOT on the
hexa-lang side were already `uchg` locked. This ceremony closes the
enforcement gap by promoting anima's two SSOT files to `uchg`.

---

## Pre-state (step 1)

```
$ ls -lO /Users/ghost/core/anima/.own /Users/ghost/core/anima/.roadmap
-rw-r--r--@ 1 ghost  staff  -  215 Apr 20 00:57 .own
-rw-r--r--@ 1 ghost  staff  - 7677 Apr 21 00:45 .roadmap
```

Flags column = `-` (no `uchg`). Both files exist, owned by `ghost:staff`.

## Backup (step 2)

Created under `docs/backup/` (note: `shared/` is a symlink to
`../nexus/shared`, unsuitable for anima-local commit; backups relocated
to the in-repo `docs/backup/` path with SHA256 preserved):

```
-rw-r--r--@ 1 ghost staff  215 Apr 21 01:49 .own.bak.20260421
-rw-r--r--@ 1 ghost staff 7677 Apr 21 01:49 .roadmap.bak.20260421
```

SHA256 (backup == live, integrity verified):

```
2062417da93f7efb1b4f4850707c316efc9394cf19b3d8e2490e325d71b72e29  .own
2062417da93f7efb1b4f4850707c316efc9394cf19b3d8e2490e325d71b72e29  .own.bak.20260421
d6273f87f1b27aa0c6eece127dde9c2830a48c406502af1681aa5eb371fbca83  .roadmap
d6273f87f1b27aa0c6eece127dde9c2830a48c406502af1681aa5eb371fbca83  .roadmap.bak.20260421
```

## Lock promotion (step 3)

No `sudo` required — owner can set `uchg` on owned files on macOS (BSD
file flags semantics).

```
$ chflags uchg /Users/ghost/core/anima/.own       # exit 0
$ chflags uchg /Users/ghost/core/anima/.roadmap   # exit 0
$ ls -lO ...
-rw-r--r--@ 1 ghost  staff  uchg  215 Apr 20 00:57 .own
-rw-r--r--@ 1 ghost  staff  uchg 7677 Apr 21 00:45 .roadmap
```

**sudo requirement**: **NOT NEEDED**. Ceremony completed as user `ghost`.
(Root privileges would only be required for `schg` / system-immutable flag.
`uchg` is user-immutable and settable by file owner.)

## Verification (step 4)

### write-test — MUST be denied

```
$ echo "test" >> /Users/ghost/core/anima/.own
zsh: operation not permitted: /Users/ghost/core/anima/.own    # exit 1 OK
$ echo "test" >> /Users/ghost/core/anima/.roadmap
zsh: operation not permitted: /Users/ghost/core/anima/.roadmap # exit 1 OK
```

Verdict: **DENIED** (both files). Enforcement active.

### unlock / relock cycle

Note: anima-side has no local `hx_lock` / `hx_unlock` binaries (those live
in hexa-lang SSOT tooling). Verification done via the underlying
`chflags uchg` / `chflags nouchg` primitive that those tools wrap.

```
$ chflags nouchg .own     # exit 0 → flag cleared
$ chflags uchg   .own     # exit 0 → flag restored
$ chflags nouchg .roadmap # exit 0
$ chflags uchg   .roadmap # exit 0
```

Content integrity preserved across the cycle (read probe OK, hashes
unchanged).

## Post-state

```
-rw-r--r--@ 1 ghost  staff  uchg  215 Apr 20 00:57 .own
-rw-r--r--@ 1 ghost  staff  uchg 7677 Apr 21 00:45 .roadmap
```

6-SSOT cross-consistency: **ALL 6 locked**. Enforcement gap closed.

## V8 SAFE_COMMIT scope

Only the following files change on disk for this ceremony:
- `docs/anima_uchg_hardening_20260421.md` (new, this doc)
- `docs/backup/.own.bak.20260421` (new, backup)
- `docs/backup/.roadmap.bak.20260421` (new, backup)

No edit to `.own` / `.roadmap` content. Flag-only state change on live
SSOT files (not tracked by git — the uchg flag does not travel in
commits, but is an on-disk runtime property).

## Rollback

If rollback needed:
```
chflags nouchg /Users/ghost/core/anima/.own /Users/ghost/core/anima/.roadmap
cp /Users/ghost/core/anima/docs/backup/.own.bak.20260421     /Users/ghost/core/anima/.own
cp /Users/ghost/core/anima/docs/backup/.roadmap.bak.20260421 /Users/ghost/core/anima/.roadmap
```
