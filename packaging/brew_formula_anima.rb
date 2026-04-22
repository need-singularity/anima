# ════════════════════════════════════════════════════════════════════════════
#  packaging/brew_formula_anima.rb — ROI N74: Homebrew formula stub
#
#  PURPOSE
#    Bottle-only Homebrew formula for the `anima` CP1 toolchain. We publish
#    pre-built bottles (per-arch tarballs in dist/) instead of building from
#    source on the user's machine — keeps install time < 10s and avoids
#    requiring the hexa toolchain at install time (only at run time).
#
#  STATUS
#    STUB. Bottle URL + SHA256 are placeholders. DO NOT push to a tap until
#    a real release artifact is staged at:
#      https://github.com/anima-org/homebrew-anima-bottles/releases/download/<ver>/...
#
#  USAGE (after real release)
#    brew tap anima-org/anima
#    brew install --bottle anima
#
#  ROADMAP REF
#    ROI N74 — brew formula (bottle 만 publish)
# ════════════════════════════════════════════════════════════════════════════

class AnimaFormula < Formula
  desc "ANIMA — n=6 grounded ALM persona toolchain (CP1 binaries)"
  homepage "https://github.com/anima-org/anima"
  version "0.1.0"
  license "MIT"

  # Bottle-only distribution — no `url`/`sha256` for a source tarball.
  # Each bottle is a pre-built artifact produced by tool/single_file_pkg.bash.
  bottle do
    root_url "https://github.com/anima-org/homebrew-anima-bottles/releases/download/v0.1.0"
    # PLACEHOLDER digests — replace with `shasum -a 256 dist/<artifact>.tar.gz`
    # output after real release build.
    sha256 cellar: :any_skip_relocation, arm64_sonoma:   "0000000000000000000000000000000000000000000000000000000000000000"
    sha256 cellar: :any_skip_relocation, arm64_ventura:  "0000000000000000000000000000000000000000000000000000000000000000"
    sha256 cellar: :any_skip_relocation, ventura:        "0000000000000000000000000000000000000000000000000000000000000000"
    sha256 cellar: :any_skip_relocation, x86_64_linux:   "0000000000000000000000000000000000000000000000000000000000000000"
  end

  # hexa runtime is required at run time to execute the .hexa sources
  # bundled in each CP1 artifact.
  depends_on "hexa"

  def install
    # Bottle layout (produced by tool/single_file_pkg.bash):
    #   dist/serve_alm_persona.bin
    #   dist/serve_alm_persona/serve_alm_persona.hexa
    #   dist/h100_post_launch_ingest.bin
    #   dist/h100_post_launch_ingest/h100_post_launch_ingest.hexa
    #   dist/an11_ensemble.bin
    #   dist/an11_ensemble/an11_ensemble.hexa
    bin.install "serve_alm_persona.bin"        => "anima_serve_alm_persona"
    bin.install "h100_post_launch_ingest.bin"  => "anima_h100_post_launch_ingest"
    bin.install "an11_ensemble.bin"            => "anima_an11_ensemble"

    # Sources go to libexec so the shims can locate them via $(dirname).
    libexec.install Dir["serve_alm_persona", "h100_post_launch_ingest", "an11_ensemble"]
  end

  def post_install
    ohai "ANIMA CP1 binaries installed:"
    ohai "  anima_serve_alm_persona      — ALM persona REST/CLI server"
    ohai "  anima_h100_post_launch_ingest — H100 launch result ingester"
    ohai "  anima_an11_ensemble          — AN11 verifier ensemble runner"
    ohai ""
    ohai "Run any with --selftest to verify install:"
    ohai "  anima_serve_alm_persona --selftest"
    ohai ""
    ohai "Roadmap reference: ROI N71-N74 (build/packaging optimization track)."
  end

  test do
    # Bottle smoke test — each binary must report PASS on --selftest.
    # In the bottle-only path these wrap `hexa <libexec_source> --selftest`.
    system "#{bin}/anima_serve_alm_persona", "--selftest"
    system "#{bin}/anima_h100_post_launch_ingest", "--selftest"
    system "#{bin}/anima_an11_ensemble", "--selftest"
  end
end
