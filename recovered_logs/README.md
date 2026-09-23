# Recovered logs

These files were **destroyed on the `logs` branch** and recovered from a stale
local git object store on 2026-09-23.

## What happened

`logrotate` runs `copytruncate` **daily** on `omega_session_*.log`: it copies
the file aside and truncates the original to zero bytes. `omega-logpush.sh`
then mirrored those zero bytes over the good copy on GitHub.

All thirteen 19-Sep session logs went to 0 bytes this way — 323 KB, the only
decision record for that day. The `logs` branch carries a single commit, so its
history could not help either.

Recovery was possible only because an earlier `git fetch` had left the old
commit in this clone's object store. **That is luck, not a backup.**

Fixed at **C480** (`deploy/omega-logpush.sh`): a file may only be overwritten
by one at least as large; a smaller source means rotation, so the archived copy
is preserved as `.partNN.log` first. Rotated files are pushed too, and detail
logs are now pushed (uncompressed, so git deltas the appended lines).

Covered by `omega_c480_logpush_test.sh`, which includes a negative control
proving the old `cp -f` destroys the data.
