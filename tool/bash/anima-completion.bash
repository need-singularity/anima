# anima CLI bash completion — matches bin/anima + tool/anima_cli/*.hexa
# mirrors tool/zsh/_anima (9 topics + status alias, 47 subcmds total)
# POSIX bash (bash 3.2+, macOS default compatible)
#
# install (interactive session):
#   source /Users/ghost/core/anima/tool/bash/anima-completion.bash
#
# install (permanent):
#   cat >> ~/.bashrc <<EOF
#   source /Users/ghost/core/anima/tool/bash/anima-completion.bash
#   EOF
#
# verify:
#   source /Users/ghost/core/anima/tool/bash/anima-completion.bash && complete -p anima

_anima_completion() {
    local cur prev words cword
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # top-level topics (9 + status alias)
    local topics="compute weight proposal cert roadmap serve paradigm inbox cost status"

    # subcommand tables (47 total)
    local sub_compute="status start stop watch cost recover ingest preflight"
    local sub_weight="status apply strategy"
    local sub_proposal="review approve reject implement archive dashboard cluster cycle"
    local sub_cert="verify graph dag"
    local sub_roadmap="status entries blockers roi"
    local sub_serve="persona api"
    local sub_paradigm="status"
    local sub_inbox="list next ack done drain"
    local sub_cost="status session per-pod history export"

    # global flags
    local global_flags="--help --version"

    # position 1: topic
    if [ "$COMP_CWORD" -eq 1 ]; then
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $(compgen -W "$global_flags" -- "$cur") )
        else
            COMPREPLY=( $(compgen -W "$topics" -- "$cur") )
        fi
        return 0
    fi

    # position 2: subcmd (dispatch on topic at words[1])
    local topic="${COMP_WORDS[1]}"
    if [ "$COMP_CWORD" -eq 2 ]; then
        local subs=""
        case "$topic" in
            compute)  subs="$sub_compute" ;;
            weight)   subs="$sub_weight" ;;
            proposal) subs="$sub_proposal" ;;
            cert)     subs="$sub_cert" ;;
            roadmap)  subs="$sub_roadmap" ;;
            serve)    subs="$sub_serve" ;;
            paradigm) subs="$sub_paradigm" ;;
            inbox)    subs="$sub_inbox" ;;
            cost)     subs="$sub_cost" ;;
            status)   subs="" ;;
        esac
        if [[ "$cur" == -* ]]; then
            COMPREPLY=( $(compgen -W "--help --json" -- "$cur") )
        else
            COMPREPLY=( $(compgen -W "$subs" -- "$cur") )
        fi
        return 0
    fi

    # position 3+: context-specific flags per topic.subcmd
    local sub="${COMP_WORDS[2]}"
    local flags="--help --json"
    case "$topic.$sub" in
        compute.status)      flags="--help --json" ;;
        compute.start)       flags="--help --dry --json" ;;
        compute.stop)        flags="--help --dry --json" ;;
        compute.watch)       flags="--help --json" ;;
        compute.cost)        flags="--help --json" ;;
        compute.recover)     flags="--help --dry --apply --json" ;;
        compute.ingest)      flags="--help --dry --apply --json" ;;
        compute.preflight)   flags="--help --json" ;;
        weight.status)       flags="--help --json" ;;
        weight.apply)        flags="--help --dry --apply --json" ;;
        weight.strategy)     flags="--help --json" ;;
        proposal.review)     flags="--help --json --top" ;;
        proposal.approve)    flags="--help --dry --apply --json" ;;
        proposal.reject)     flags="--help --dry --json" ;;
        proposal.implement)  flags="--help --dry --apply --json" ;;
        proposal.archive)    flags="--help --dry --json" ;;
        proposal.dashboard)  flags="--help --json --top" ;;
        proposal.cluster)    flags="--help --dry --apply --json" ;;
        proposal.cycle)      flags="--help --dry --apply --json" ;;
        cert.verify)         flags="--help --json" ;;
        cert.graph)          flags="--help --json" ;;
        cert.dag)            flags="--help --json" ;;
        roadmap.status)      flags="--help --json" ;;
        roadmap.entries)     flags="--help --json --top" ;;
        roadmap.blockers)    flags="--help --json" ;;
        roadmap.roi)         flags="--help --json --top" ;;
        serve.persona)       flags="--help --dry --json" ;;
        serve.api)           flags="--help --dry --json" ;;
        paradigm.status)     flags="--help --json" ;;
        inbox.list)          flags="--help --json --top" ;;
        inbox.next)          flags="--help --json" ;;
        inbox.ack)           flags="--help --dry --apply --json" ;;
        inbox.done)          flags="--help --dry --apply --json" ;;
        inbox.drain)         flags="--help --dry --apply --json" ;;
        cost.status)         flags="--help --json" ;;
        cost.session)        flags="--help --json" ;;
        cost.per-pod)        flags="--help --json" ;;
        cost.history)        flags="--help --json --top" ;;
        cost.export)         flags="--help --json" ;;
    esac

    # --top N expects an integer (no completion for value beyond hint)
    if [ "$prev" = "--top" ]; then
        COMPREPLY=( $(compgen -W "5 10 20 50 100" -- "$cur") )
        return 0
    fi

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$flags" -- "$cur") )
    fi
    return 0
}

complete -F _anima_completion anima
