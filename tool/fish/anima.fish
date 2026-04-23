# anima CLI fish completion — matches bin/anima + tool/anima_cli/*.hexa
# mirrors tool/bash/anima-completion.bash + tool/zsh/_anima
# 9 topics + status alias, 39 unique subcmds, context-specific flags
# fish 3+ standard completion format
#
# install:
#   cp /Users/ghost/core/anima/tool/fish/anima.fish ~/.config/fish/completions/
#   # fish auto-loads on next prompt; or `exec fish` to restart
#
# verify:
#   complete -c anima    # lists all rules
#   anima <TAB>          # 10 topics
#   anima compute <TAB>  # 8 subcmds

# ────────────────────────────────────────────────────────────
# global flags (always available)
# ────────────────────────────────────────────────────────────
complete -c anima -l help    -d "show help"
complete -c anima -l version -d "show version"
complete -c anima -l json    -d "JSON output"
complete -c anima -l dry     -d "dry-run (preview)"
complete -c anima -l apply   -d "apply mutation"
complete -c anima -l top     -d "limit top-N results" -x

# ────────────────────────────────────────────────────────────
# position 1 — topics (9 + status alias)
# ────────────────────────────────────────────────────────────
complete -c anima -n "__fish_use_subcommand" -a "compute"  -d "pod lifecycle (status|start|stop|watch|cost|recover|ingest|preflight)"
complete -c anima -n "__fish_use_subcommand" -a "weight"   -d "weight precache (status|apply|strategy)"
complete -c anima -n "__fish_use_subcommand" -a "proposal" -d "proposal stack (review|approve|reject|implement|archive|dashboard|cluster|cycle)"
complete -c anima -n "__fish_use_subcommand" -a "cert"     -d "breakthrough cert (verify|graph|dag)"
complete -c anima -n "__fish_use_subcommand" -a "roadmap"  -d "roadmap engine (status|entries|blockers|roi)"
complete -c anima -n "__fish_use_subcommand" -a "serve"    -d "serving layer (persona|api)"
complete -c anima -n "__fish_use_subcommand" -a "paradigm" -d "unified paradigm status"
complete -c anima -n "__fish_use_subcommand" -a "inbox"    -d "proposal inbox (list|next|ack|done|drain)"
complete -c anima -n "__fish_use_subcommand" -a "cost"     -d "session cost (status|session|per-pod|history|export)"
complete -c anima -n "__fish_use_subcommand" -a "status"   -d "global dashboard (alias)"

# ────────────────────────────────────────────────────────────
# position 2 — subcmds per topic (39 unique)
# ────────────────────────────────────────────────────────────
# compute (8)
complete -c anima -n "__fish_seen_subcommand_from compute" -a "status"    -d "pod status"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "start"     -d "start pod"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "stop"      -d "stop pod"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "watch"     -d "watch pod events"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "cost"      -d "pod cost"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "recover"   -d "recover pod"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "ingest"    -d "ingest pod manifest"
complete -c anima -n "__fish_seen_subcommand_from compute" -a "preflight" -d "preflight check"

# weight (3)
complete -c anima -n "__fish_seen_subcommand_from weight" -a "status"   -d "weight precache status"
complete -c anima -n "__fish_seen_subcommand_from weight" -a "apply"    -d "apply weight strategy"
complete -c anima -n "__fish_seen_subcommand_from weight" -a "strategy" -d "show strategy"

# proposal (8)
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "review"    -d "review pending proposals"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "approve"   -d "approve proposal"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "reject"    -d "reject proposal"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "implement" -d "implement proposal"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "archive"   -d "archive proposal"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "dashboard" -d "proposal dashboard"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "cluster"   -d "cluster proposals"
complete -c anima -n "__fish_seen_subcommand_from proposal" -a "cycle"     -d "run proposal cycle"

# cert (3)
complete -c anima -n "__fish_seen_subcommand_from cert" -a "verify" -d "verify breakthrough cert"
complete -c anima -n "__fish_seen_subcommand_from cert" -a "graph"  -d "cert graph"
complete -c anima -n "__fish_seen_subcommand_from cert" -a "dag"    -d "cert DAG"

# roadmap (4)
complete -c anima -n "__fish_seen_subcommand_from roadmap" -a "status"   -d "roadmap status"
complete -c anima -n "__fish_seen_subcommand_from roadmap" -a "entries"  -d "list entries"
complete -c anima -n "__fish_seen_subcommand_from roadmap" -a "blockers" -d "show blockers"
complete -c anima -n "__fish_seen_subcommand_from roadmap" -a "roi"      -d "ROI ranking"

# serve (2)
complete -c anima -n "__fish_seen_subcommand_from serve" -a "persona" -d "serve persona"
complete -c anima -n "__fish_seen_subcommand_from serve" -a "api"     -d "serve api"

# paradigm (1)
complete -c anima -n "__fish_seen_subcommand_from paradigm" -a "status" -d "paradigm status"

# inbox (5)
complete -c anima -n "__fish_seen_subcommand_from inbox" -a "list"  -d "list inbox"
complete -c anima -n "__fish_seen_subcommand_from inbox" -a "next"  -d "next inbox item"
complete -c anima -n "__fish_seen_subcommand_from inbox" -a "ack"   -d "ack item"
complete -c anima -n "__fish_seen_subcommand_from inbox" -a "done"  -d "mark done"
complete -c anima -n "__fish_seen_subcommand_from inbox" -a "drain" -d "drain inbox"

# cost (5)
complete -c anima -n "__fish_seen_subcommand_from cost" -a "status"  -d "cost status"
complete -c anima -n "__fish_seen_subcommand_from cost" -a "session" -d "session cost"
complete -c anima -n "__fish_seen_subcommand_from cost" -a "per-pod" -d "per-pod cost"
complete -c anima -n "__fish_seen_subcommand_from cost" -a "history" -d "cost history"
complete -c anima -n "__fish_seen_subcommand_from cost" -a "export"  -d "export cost data"
