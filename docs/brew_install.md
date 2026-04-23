# Homebrew install — anima CP1 toolchain (ROI N74)

> Status: **STUB** — `packaging/brew_formula_anima.rb` ships placeholder
> bottle digests. Do not run the commands below against a real tap until a
> release artifact is staged. This doc captures the **target** install UX.

## Target install command

```bash
brew tap anima-org/anima
brew install --bottle anima
```

Expected output:

```
==> Pouring anima-0.1.0.arm64_sonoma.bottle.tar.gz
==> ANIMA CP1 binaries installed:
==>   anima_serve_alm_persona      — ALM persona REST/CLI server
==>   anima_h100_post_launch_ingest — H100 launch result ingester
==>   anima_an11_ensemble          — AN11 verifier ensemble runner
==>
==> Run any with --selftest to verify install:
==>   anima_serve_alm_persona --selftest
==>
==> Roadmap reference: ROI N71-N74 (build/packaging optimization track).
```

## Verification

```bash
anima_serve_alm_persona --selftest
anima_h100_post_launch_ingest --selftest
anima_an11_ensemble --selftest
```

All three must exit 0.

## Producing a real release (operator only)

1. `bash tool/single_file_pkg.bash` — stages `dist/<name>.bin` shims +
   `dist/<name>/` source dirs.
2. Tar each per-arch tree:
   `tar -czf anima-0.1.0.arm64_sonoma.bottle.tar.gz -C dist .`
3. Compute digest: `shasum -a 256 anima-0.1.0.arm64_sonoma.bottle.tar.gz`.
4. Replace the matching `0000…` line in `packaging/brew_formula_anima.rb`.
5. Upload tarball to
   `github.com/anima-org/homebrew-anima-bottles/releases/v0.1.0/`.
6. Open PR against `anima-org/homebrew-anima` tap with the updated formula.

## Constraints honoured

- Bottle-only — never builds from source on user host.
- `depends_on "hexa"` — runtime dependency only.
- No system binaries are stripped during install; bottles already contain
  stripped artifacts (see `tool/bin_reduce.bash`, ROI N72).

## See also

- `tool/aot_cache_audit.hexa` — N71
- `tool/bin_reduce.bash` — N72
- `tool/single_file_pkg.bash` — N73
- `state/build_packaging_audit.json` — rolled-up N71-N74 status
