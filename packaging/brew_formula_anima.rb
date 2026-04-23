# ════════════════════════════════════════════════════════════════════════════
#  packaging/brew_formula_anima.rb — Y5 brew tap for anima CLI
#
#  PURPOSE
#    Homebrew formula for the `anima` unified CLI (bin/anima + the hexa
#    modules under tool/anima_cli/). Installs:
#      - bin/anima                 -> #{HOMEBREW_PREFIX}/bin/anima
#      - tool/anima_cli/*.hexa     -> share/anima/anima_cli/
#      - docs/man/anima.1          -> share/man/man1/anima.1
#      - tool/bash/anima-completion.bash  -> bash completion dir
#      - tool/zsh/_anima                  -> zsh completion dir
#      - tool/fish/anima.fish             -> fish completion dir
#
#  TAP LAYOUT (see docs/brew_tap_install.md)
#    brew tap need-singularity/anima      # resolves to
#                                         # github.com/need-singularity/homebrew-anima
#    brew install anima
#
#  STATUS
#    STUB — sha256 below is a placeholder. Replace after staging the real
#    release tarball at github.com/need-singularity/anima/releases/v<ver>.
#
#  ROADMAP REF
#    Y5 — brew tap for anima CLI (N74 predecessor: bottle-only CP1 formula)
# ════════════════════════════════════════════════════════════════════════════

class Anima < Formula
  desc "ANIMA — unified CLI for the β-main paradigm (proposal stack + auto-evolution)"
  homepage "https://github.com/need-singularity/anima"
  url "https://github.com/need-singularity/anima/archive/refs/tags/v0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  version "0.1.0"
  license "MIT"
  head "https://github.com/need-singularity/anima.git", branch: "main"

  # hexa-lang is the runtime for every .hexa module dispatched by bin/anima.
  # When the upstream hexa-lang tap is published, uncomment the first form
  # and remove the caveat. Until then we emit a post-install note (see
  # `caveats` below) and treat hexa as a soft runtime dependency.
  #
  # depends_on "need-singularity/hexa/hexa-lang"
  depends_on "bash"

  def install
    # Core dispatcher — single bash entry point.
    bin.install "bin/anima"

    # Hexa modules + shared helpers consumed by bin/anima via $(dirname).
    # Canonical layout expected by the dispatcher:
    #   #{HOMEBREW_PREFIX}/share/anima/anima_cli/<topic>.hexa
    (share/"anima/anima_cli").install Dir["tool/anima_cli/*.hexa"]
    (share/"anima/anima_cli").install "tool/anima_cli/man_install.bash"

    # Man page — Homebrew auto-links share/man/man1/* into MANPATH.
    man1.install "docs/man/anima.1"

    # Shell completions — Homebrew exports each of these into the
    # corresponding completions directory at install time.
    bash_completion.install "tool/bash/anima-completion.bash" => "anima"
    zsh_completion.install  "tool/zsh/_anima"
    fish_completion.install "tool/fish/anima.fish"
  end

  def caveats
    <<~EOS
      anima dispatches to hexa modules under:
        #{opt_share}/anima/anima_cli/

      Runtime requirement (not yet a brew dependency):
        hexa-lang — once `need-singularity/hexa` tap ships a formula,
        run:   brew tap need-singularity/hexa && brew install hexa-lang
        until then, build from source:
          git clone https://github.com/need-singularity/hexa-lang
          cd hexa-lang && make install

      Verify install:
        anima --version
        man anima

      Enable completions (if not auto-loaded):
        bash:  source "$(brew --prefix)/etc/bash_completion.d/anima"
        zsh:   add `$(brew --prefix)/share/zsh/site-functions` to $fpath
        fish:  already picked up from $(brew --prefix)/share/fish/vendor_completions.d
    EOS
  end

  test do
    # Smoke: --version prints a semver-like string and exits 0.
    assert_match(/\d+\.\d+\.\d+/, shell_output("#{bin}/anima --version"))

    # Smoke: --help lists the topic dispatcher banner.
    assert_match("anima", shell_output("#{bin}/anima --help 2>&1", 0).downcase)

    # Man page is discoverable.
    assert_predicate man1/"anima.1", :exist?

    # Completions are installed to the canonical locations.
    assert_predicate bash_completion/"anima", :exist?
    assert_predicate zsh_completion/"_anima",  :exist?
    assert_predicate fish_completion/"anima.fish", :exist?
  end
end
