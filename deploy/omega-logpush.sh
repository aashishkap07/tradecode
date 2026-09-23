#!/usr/bin/env bash
# OMEGA V60 — push the logs to GitHub so they can be analysed  [C472, hardened C474]
#
# WHY THIS EXISTS. The logs live on your server. Nobody analysing them can
# reach your server. Without this you have to remember to download files and
# attach them, so analysis happens when you remember, not when something
# interesting happens.
#
#   omega-logpush.sh            push once
#   omega-logpush.sh --check    check everything is set up, change nothing
#   omega-logpush.sh --setup    print the exact steps to give it push access
#
# Install (after --check passes):
#   sudo cp omega-logpush.sh /usr/local/bin/ && sudo chmod +x /usr/local/bin/omega-logpush.sh
#   echo '17 * * * * omega /usr/local/bin/omega-logpush.sh' | sudo tee /etc/cron.d/omega-logpush

set -uo pipefail

REPO="${OMEGA_HOME:-/home/omega/omega}"
BRANCH="${OMEGA_LOG_BRANCH:-logs}"
# C480: ON by default. The detail log is where per-trade margin, conviction,
# ATR and the drawdown-pause events live, and without it the archive cannot
# answer why a position was sized the way it was. Set PUSH_DETAIL=0 to skip it.
PUSH_DETAIL="${PUSH_DETAIL:-1}"
TOKEN_FILE="${OMEGA_TOKEN_FILE:-/etc/omega.token}"

# C474: cron has no terminal. Without this git BLOCKS forever on
# "Username for 'https://github.com':" instead of failing, and the job piles up
# one stuck process an hour until the box runs out of them.
export GIT_TERMINAL_PROMPT=0
export GIT_ASKPASS=/bin/true

say()  { printf '\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m !! %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m !! %s\033[0m\n' "$*" >&2; logger -t omega-logpush "$*"; exit 1; }

# ─────────────────────────────────────────────────────────────────────────
setup_help() {
# ═══ C477: --setup DOES THE WORK IT CAN, AND PRINTS ONLY WHAT IT CANNOT ══
# The first version printed a page of instructions containing PROSE and
# BACKTICKS -- "(replace OWNER/REPO -- `git ... remote -v` shows yours)". The
# operator pasted the whole block, bash opened a command substitution on the
# unmatched backtick and sat at a `>` continuation prompt, and the literal
# words "git -C /home/omega/omega remote -v" ended up inside the push URL:
#     git@github.com:git -C /home/omega/omega remote -v.git
# Instructions that are unsafe to paste are a defect in the instructions. This
# now derives owner/repo from the existing remote, sets the push URL itself,
# creates the key and the ssh config itself, and asks the human for the ONE
# thing only a human can do: paste a public key into a web page.
    # C477: NEVER assume a home directory is /home/<name>. It is for omega and
    # it is not for root (/root), and a wrong path here fails as "ssh-keygen
    # failed" with no clue why. Ask the password database.
    local me home url owner_repo keyfile sshdir
    me="$(id -un)"
    home="$(getent passwd "$me" | cut -d: -f6)"
    [ -n "$home" ] || home="${HOME:-/home/$me}"
    sshdir="$home/.ssh"
    keyfile="$sshdir/omega_deploy"
    mkdir -p "$sshdir" && chmod 700 "$sshdir"
    url="$(git -C "$REPO" remote get-url origin 2>/dev/null)"
    owner_repo="$(printf '%s' "$url" \
        | sed -E 's#^git@[^:]+:##; s#^https?://[^/]+/##; s#\.git$##')"
    if [ -z "$owner_repo" ]; then
        warn "could not work out owner/repo from the origin URL ($url)"
        owner_repo="OWNER/REPO"
    fi

    if [ ! -f "$keyfile" ]; then
        say "Creating a deploy key for $(id -un)"
        command -v ssh-keygen >/dev/null 2>&1 \
            || die "ssh-keygen is not installed. Fix: sudo apt-get install -y openssh-client"
        # C477: show the REAL error. "ssh-keygen failed" with the output
        # swallowed sent me looking for a permissions problem when the binary
        # simply was not there.
        _kg="$(ssh-keygen -t ed25519 -f "$keyfile" -N "" -C "omega-logpush" 2>&1)" \
            || die "ssh-keygen failed: $_kg"
    else
        say "Deploy key already exists at $keyfile"
    fi

    if ! grep -q "omega_deploy" "$sshdir/config" 2>/dev/null; then
        say "Telling git to use it for github.com"
        {
            echo "Host github.com"
            echo "  IdentityFile $keyfile"
            echo "  IdentitiesOnly yes"
            echo "  StrictHostKeyChecking accept-new"
        } >> "$sshdir/config"
        chmod 600 "$sshdir/config"
    else
        say "ssh config already points at the deploy key"
    fi

    say "Pointing pushes at SSH for ${owner_repo}"
    git -C "$REPO" remote set-url --push origin "git@github.com:${owner_repo}.git"
    # C477: read back the STORED value. Some git builds keep reporting the
    # fetch URL from `remote -v` / `get-url --push` even after the pushurl is
    # set, which reads like the command silently failed when it did not.
    echo "    push URL: $(git -C "$REPO" config --get remote.origin.pushurl)"

    echo
    echo "────────────────────────────────────────────────────────────────"
    echo " ONE STEP LEFT, and only you can do it."
    echo "────────────────────────────────────────────────────────────────"
    echo
    echo " 1. Copy the line between the markers below (the key only):"
    echo
    echo "--------8<-------- COPY FROM HERE --------8<--------"
    cat "${keyfile}.pub"
    echo "--------8<--------- TO HERE ------------8<--------"
    echo
    echo " 2. Open:  https://github.com/${owner_repo}/settings/keys"
    echo "    Add deploy key -> Title: omega-logpush -> paste the key"
    echo "    TICK 'Allow write access'   <- nothing works without it"
    echo "    Add key."
    echo
    echo " 3. Come back and run:"
    echo "        $0 --check"
    echo
    echo " (If the key is already added, just run --check.)"
    echo
}

[ "${1:-}" = "--setup" ] && { setup_help; exit 0; }

# ─────────────────────────────────────────────────────────────────────────
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

problems=0
check() {  # check <description> <command...>
    local d="$1"; shift
    if "$@" >/dev/null 2>&1; then printf '  OK   %s\n' "$d"
    else printf '  \033[1;31mFAIL\033[0m %s\n' "$d"; problems=$((problems+1)); fi
}

if [ "$CHECK_ONLY" = 1 ]; then
    say "Checking the log push as user $(id -un)"
    check "the repo exists"                 test -d "$REPO/.git"
    check "this user can write to the repo" test -w "$REPO"
    # ═══ C475: CHECK WHAT THE OPERATION NEEDS, NOT SOMETHING NEARBY ═══════
    # The first version checked `test -w "$REPO"` -- the WORKING directory --
    # and reported all-clear while the real push died with "insufficient
    # permission for adding an object to repository database
    # .git/objects". Git writes objects into .git, not into the checkout, and
    # a repo cloned or pulled with sudo has root-owned objects. A check that
    # passes while the operation fails is worse than no check: it sends the
    # operator to wire up a cron job that can never work.
    check "this user can write git objects (.git/objects)" test -w "$REPO/.git/objects"
    check "the token file is readable (so the scrubber can redact it)" \
          test -r "$TOKEN_FILE"
    check "git will not block on a password prompt" test "$GIT_TERMINAL_PROMPT" = "0"
    # C476: an unpushed commit is invisible to every other check here, and it
    # is precisely what a silently-failing push leaves behind.
    if [ -d "$REPO/.logpush" ]; then
        _un="$(git -C "$REPO/.logpush" rev-list --count "origin/${BRANCH}..HEAD" 2>/dev/null || echo 0)"
        if [ "${_un:-0}" -gt 0 ]; then
            printf '  \033[1;33mWARN\033[0m %s commit(s) are committed locally but NOT on the remote\n' "$_un"
            printf '       a normal run will push them; if it does not, the push is failing\n'
        else
            printf '  OK   nothing is waiting to be pushed\n'
        fi
    fi
    # ls-remote succeeds on a PUBLIC repo with no credentials at all, so it
    # answers "can I read?" when the question is "can I write?". --dry-run
    # asks the real one.
    # C476: test push capability WITHOUT proposing a real ref update. Asking
    # to push the CODE branch's HEAD onto refs/heads/logs is a non-fast-forward
    # the moment the logs branch has any history of its own, so this reported
    # "cannot PUSH" on a setup where pushing worked perfectly -- a false
    # failure, which sends the operator hunting a credential problem that does
    # not exist. Push the logs worktree's own HEAD when it exists (a genuine
    # fast-forward), and otherwise a scratch ref name that cannot conflict.
    if [ -d "$REPO/.logpush" ]; then
        _pushsrc="$REPO/.logpush"; _pushref="refs/heads/${BRANCH}"
    else
        _pushsrc="$REPO"; _pushref="refs/heads/__omega_push_check__"
    fi
    if git -C "$_pushsrc" push --dry-run -q origin "HEAD:${_pushref}" >/dev/null 2>&1; then
        printf '  OK   this user can PUSH to the remote\n'
    elif git -C "$REPO" ls-remote --exit-code origin >/dev/null 2>&1; then
        printf '  \033[1;31mFAIL\033[0m the remote is reachable but this user cannot PUSH — run: %s --setup\n' "$0"
        problems=$((problems+1))
    else
        printf '  \033[1;31mFAIL\033[0m the remote rejected this user — run: %s --setup\n' "$0"
        problems=$((problems+1))
    fi
    echo
    if [ "$problems" -eq 0 ]; then
        say "All good. Wire it up:"
        echo "    echo '17 * * * * $(id -un) $0' | sudo tee /etc/cron.d/omega-logpush"
        exit 0
    fi
    die "$problems problem(s) above. Run '$0 --setup' for the fix."
fi

# ─────────────────────────────────────────────────────────────────────────
cd "$REPO" || die "cannot enter $REPO"

# C475: fail here, with the cure, rather than 200 lines later inside git.
if [ ! -w "$REPO/.git/objects" ]; then
    die "$(id -un) cannot write to $REPO/.git/objects — the repo was cloned or
     pulled with sudo, so git's object store belongs to root.
     Fix: sudo chown -R $(id -un):$(id -un) $REPO
     Then pull as this user from now on, NOT as root:
         sudo -u $(id -un) git -C $REPO pull
     A root-run 'git pull' re-creates root-owned objects and breaks it again."
fi

# ═══ C474: A SCRUBBER THAT CANNOT SCRUB MUST NOT PUSH ═══════════════════
# The first version did `[ -f "$TOKEN_FILE" ] && TOK=$(cat ...)`. Run as the
# omega user against a root-only 600 file, that prints "Permission denied",
# leaves TOK empty, and redacts NOTHING — while continuing happily to push.
# That is the same defect as the value-class bug this script already had: a
# scrubber whose failure mode is "quietly does nothing" is worse than no
# scrubber, because it is trusted. If the token exists and cannot be read,
# stop, and name the one command that fixes it.
TOK=""
if [ -e "$TOKEN_FILE" ]; then
    if [ -r "$TOKEN_FILE" ]; then
        TOK="$(cat "$TOKEN_FILE")"
    else
        die "cannot read $TOKEN_FILE as $(id -un), so the control token could not be
     redacted from the logs — refusing to push rather than push unscrubbed.
     Fix: sudo chgrp $(id -un) $TOKEN_FILE && sudo chmod 640 $TOKEN_FILE"
    fi
fi

# A worktree keeps the logs branch entirely separate from the code branch, so
# this can never commit, stash or disturb the checkout the bot runs from.
WT="${REPO}/.logpush"
if [ ! -e "$WT/.git" ]; then
    git worktree add -B "$BRANCH" "$WT" >/dev/null 2>&1 || {
        git fetch origin "$BRANCH" >/dev/null 2>&1
        git worktree add "$WT" "$BRANCH" >/dev/null 2>&1 || die "could not create the logs worktree"
    }
fi

mkdir -p "$WT/logs"

# ═══ C480: THE ARCHIVE MUST NEVER SHRINK ═════════════════════════
# This script used to `cp -f` the live log over whatever was on the branch.
# That is correct only while a log file GROWS. logrotate runs `copytruncate`
# DAILY on omega_session_* and omega_detail_*: it copies the file aside and
# then truncates the original to ZERO BYTES. The next run of this script then
# faithfully mirrored those zero bytes over the good copy on GitHub.
#
# MEASURED, not hypothetical: omega_session_20260919_003314.log was 90,149
# bytes on the branch and became 0. All thirteen 19-Sep session logs were
# destroyed the same way -- 323 KB of the only decision record for that day.
# They were recoverable only because an older fetch still sat in a local
# object store, and the branch is force-pushed, so its history could not help.
#
# Two rules now, and between them nothing can be lost:
#   1. a file may only be overwritten by one AT LEAST AS LARGE. A smaller
#      source means the live file was rotated, so the archived copy is
#      preserved under a .partNN. name FIRST and the new (restarted) file is
#      then stored alongside it.
#   2. the rotated files logrotate leaves behind (.log.1, .log.N.gz) are
#      pushed too, so the content that was moved aside also reaches GitHub.
keep() {
    # keep <source-file> -> copies into $WT/logs, never destroying bytes
    local src="$1" base dst ssz dsz n
    base="$(basename "$src")"
    dst="$WT/logs/$base"
    if [ ! -e "$dst" ]; then
        cp -f "$src" "$dst" && copied=$((copied+1))
        return
    fi
    ssz=$(stat -c %s "$src" 2>/dev/null || echo 0)
    dsz=$(stat -c %s "$dst" 2>/dev/null || echo 0)
    if [ "$ssz" -ge "$dsz" ]; then
        cp -f "$src" "$dst" && copied=$((copied+1))
        return
    fi
    # Source is SMALLER: the live file was rotated out from under us.
    # Park what we already have before taking the new, shorter file.
    n=1
    while [ -e "$WT/logs/${base%.log}.part$(printf '%02d' $n).log" ]; do
        n=$((n+1))
        [ "$n" -gt 99 ] && { warn "too many parts for $base -- not overwriting"; return; }
    done
    mv "$dst" "$WT/logs/${base%.log}.part$(printf '%02d' $n).log"
    logger -t omega-logpush "$base shrank ${dsz}->${ssz} (logrotate); preserved as part$(printf '%02d' $n)"
    cp -f "$src" "$dst" && copied=$((copied+2))
}

copied=0
for f in "$REPO"/omega_report_*.log "$REPO"/omega_session_*.log; do
    [ -e "$f" ] || continue
    keep "$f"
done
if [ "$PUSH_DETAIL" = "1" ]; then
    # The detail log is the ONLY place per-trade sizing, margin, conviction and
    # the drawdown-pause events are recorded, and none of it was reaching the
    # archive -- which is why three separate questions about this bot's
    # behaviour could not be answered from the pushed data.
    #
    # Stored UNCOMPRESSED on purpose. It is an append-only text file pushed
    # once an hour, so git delta-compresses each new version against the last
    # and stores only the lines that were added. Gzipping it first would defeat
    # that completely: every hour would become a fresh incompressible blob.
    for f in "$REPO"/omega_detail_*.log; do
        [ -e "$f" ] || continue
        keep "$f"
    done
fi
# C480 rule 2: whatever logrotate moved aside.
for f in "$REPO"/omega_*.log.1 "$REPO"/omega_*.log.*.gz; do
    [ -e "$f" ] || continue
    case "$f" in *.gz) cp -f "$f" "$WT/logs/$(basename "$f")" ;;
                  *)   gzip -c "$f" > "$WT/logs/$(basename "$f").gz" ;;
    esac
    copied=$((copied+1))
done
for f in "$REPO"/data/mode_v60.json "$REPO"/data/state_v60.json; do
    [ -e "$f" ] && cp -f "$f" "$WT/logs/"
done
[ "$copied" -gt 0 ] || exit 0

# ─── SCRUB ───────────────────────────────────────────────────────────────
if [ -n "$TOK" ]; then
    grep -rlF "$TOK" "$WT/logs" 2>/dev/null | while read -r h; do
        sed -i "s|${TOK}|<TOKEN-REDACTED>|g" "$h"
    done
fi
# The value class MUST include _ and -. Exchange keys look like
# "bg_9f8a7b6c..." and a class of [A-Za-z0-9/+] stops at the underscore,
# matching two characters, failing the {16,} length test and redacting NOTHING.
SECRET_RE='(api[_-]?key|api[_-]?secret|passphrase|secret|password)'
grep -rlEi "${SECRET_RE}[\"':= ]+[A-Za-z0-9/+_-]{16,}" "$WT/logs" 2>/dev/null | while read -r h; do
    sed -i -E "s/(${SECRET_RE})([\"':= ]+)[A-Za-z0-9\/+_-]{16,}/\1\3<REDACTED>/gI" "$h"
done
# Last line of defence: if the token is somehow still present, do not push.
if [ -n "$TOK" ] && grep -rqF "$TOK" "$WT/logs" 2>/dev/null; then
    die "the control token is STILL present after scrubbing — refusing to push"
fi

cd "$WT" || die "cannot enter the worktree"
# ═══ C476: "NOTHING TO COMMIT" IS NOT "NOTHING TO PUSH" ═══════════════
# The previous version was:
#     git add -A logs
#     git diff --cached --quiet && exit 0
# If a run COMMITTED and then failed to PUSH -- which is exactly what happened
# the first time this ran for real -- the next run finds nothing new to stage,
# exits 0, and never touches the pending commit. Every hour after that it
# reports success and pushes nothing, forever, while the operator believes
# their logs are reaching GitHub. The commit sat local-only and the `logs`
# branch never appeared on the remote at all.
# Staging and pushing are two different questions. Ask them separately.
# ═══ C478: -f, BECAUSE THE REPO'S OWN .gitignore WAS EATING THE LOGS ═══
# The code branch ignores omega_report_*.log / omega_session_*.log to keep the
# headless boot test's residue out of source. Unanchored, those patterns match
# at any depth, so they silently ignored the very files this script exists to
# push: it copied 26, git staged 2, and the commit message said 26 because the
# count came from the COPY loop rather than from what was committed. The
# ignore rules are anchored now, but -f makes this independent of whatever
# .gitignore happens to be on the logs branch.
git add -A -f logs
if git diff --cached --quiet; then
    :                                          # nothing new to record
else
    # Count what is ACTUALLY going in, not what was copied.
    staged="$(git diff --cached --name-only | grep -c '^logs/' || true)"
    git -c user.name='omega-bot' -c user.email='omega@localhost' \
        commit -q -m "logs: $(date -u '+%Y-%m-%d %H:%M UTC') (${staged} file(s))" \
        || die "commit failed"
fi

# And confirm the log files really are in the tree. A commit that quietly
# contains only the two JSON state files looks identical, from outside, to one
# that worked.
_n_logs="$(git ls-tree -r --name-only HEAD -- logs 2>/dev/null | grep -c '\.log$' || true)"
if [ "${_n_logs:-0}" -eq 0 ] && [ "$copied" -gt 0 ]; then
    die "copied $copied file(s) but the commit contains NO .log files --
     something is ignoring them. Check: git -C $WT check-ignore -v logs/*.log"
fi

# Are we ahead of the remote? A branch that does not exist there yet always is.
if git rev-parse --quiet --verify "refs/remotes/origin/${BRANCH}" >/dev/null 2>&1; then
    ahead="$(git rev-list --count "origin/${BRANCH}..HEAD" 2>/dev/null || echo 1)"
else
    ahead=1
fi
[ "${ahead:-0}" -gt 0 ] || exit 0              # genuinely up to date

pushed=0
for i in 1 2 3 4; do
    if git push -q origin "HEAD:${BRANCH}" 2>/dev/null; then pushed=1; break; fi
    sleep $((2 ** i))
done
[ "$pushed" = 1 ] || die "push failed after 4 attempts — run '$0 --check'"

# ═══ C476: PROVE IT LANDED. ═══════════════════════════════════════════
# A push that "succeeded" locally is a claim. Ask the remote what it holds
# and compare. This is the check that found the bug above -- the script said
# it was fine, and `git ls-remote` said the branch did not exist.
local_head="$(git rev-parse HEAD)"
remote_head="$(git ls-remote origin "refs/heads/${BRANCH}" 2>/dev/null | cut -f1)"
if [ "$remote_head" != "$local_head" ]; then
    die "push reported success but the remote does not have it.
     local  $local_head
     remote ${remote_head:-<branch missing>}"
fi
exit 0
