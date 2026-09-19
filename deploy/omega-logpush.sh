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
PUSH_DETAIL="${PUSH_DETAIL:-0}"
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
cat <<'HELP'
GIVING THE LOG PUSH ACCESS TO YOUR REPO

The push runs as the `omega` user, which has no GitHub credentials. A DEPLOY
KEY is the right answer: it grants write access to THIS ONE REPOSITORY and
nothing else, it is revocable from the repo's settings page, and unlike a
personal access token it cannot touch your other repos if the server is ever
compromised.

1. On the server, make a key for the omega user:

     sudo -u omega ssh-keygen -t ed25519 -f /home/omega/.ssh/omega_deploy -N "" -C "omega-logpush"
     sudo -u omega cat /home/omega/.ssh/omega_deploy.pub

2. Copy that whole line. On github.com open:
     your repo -> Settings -> Deploy keys -> Add deploy key
   Title: omega-logpush
   Key:   paste it
   TICK "Allow write access"          <-- easy to miss, and nothing works without it
   Add key.

3. Back on the server, tell git to use that key and talk SSH:

     sudo -u omega tee -a /home/omega/.ssh/config >/dev/null <<'EOF'
     Host github.com
       IdentityFile /home/omega/.ssh/omega_deploy
       IdentitiesOnly yes
       StrictHostKeyChecking accept-new
     EOF
     sudo -u omega chmod 600 /home/omega/.ssh/config
     sudo git -C /home/omega/omega remote set-url --push origin git@github.com:OWNER/REPO.git

   (replace OWNER/REPO — `git -C /home/omega/omega remote -v` shows yours)

4. Let the omega user read the token file, so the scrubber can actually redact
   it. Group-readable, not world-readable:

     sudo chgrp omega /etc/omega.token && sudo chmod 640 /etc/omega.token

5. Check, then wire the cron job:

     sudo -u omega /usr/local/bin/omega-logpush.sh --check
HELP
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
copied=0
for f in "$REPO"/omega_report_*.log "$REPO"/omega_session_*.log; do
    [ -e "$f" ] || continue
    cp -f "$f" "$WT/logs/" && copied=$((copied+1))
done
if [ "$PUSH_DETAIL" = "1" ]; then
    for f in "$REPO"/omega_detail_*.log; do
        [ -e "$f" ] || continue
        cp -f "$f" "$WT/logs/" && copied=$((copied+1))
    done
fi
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
git add -A logs
if git diff --cached --quiet; then
    :                                          # nothing new to record
else
    git -c user.name='omega-bot' -c user.email='omega@localhost' \
        commit -q -m "logs: $(date -u '+%Y-%m-%d %H:%M UTC') ($copied file(s))" \
        || die "commit failed"
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
