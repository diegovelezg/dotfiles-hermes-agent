# Skills Git Recovery — `~/.hermes/skills/` Restore Procedure

## Problem

Custom skills (e.g. `diego-*`) exist in the git history of `~/.hermes/skills/` but are missing from the filesystem. They may also appear in `.archive/` as orphaned copies.

**Symptoms:**
- `hermes skills list` shows the skill as `local` but `find ~/.hermes/skills -name "*skillname*"` returns nothing
- `git status` in `~/.hermes/skills/` shows the skill directory as `deleted`
- The blobs exist in `git ls-tree -r HEAD -- path/` but `git checkout HEAD -- path/` fails with "pathspec did not match any file(s) known to git"

**Root cause:** The skills directory is itself a git repo. Skills were deleted from the working tree (or never checked out) but the HEAD tree still references them.

## Recovery Procedure

```bash
# 1. Verify blobs exist in HEAD
git -C ~/.hermes/skills ls-tree -r HEAD -- diego-buenos-dias/

# 2. Attempt direct checkout from repo root
git -C ~/.hermes/skills checkout HEAD -- diego-buenos-dias/ diego-read-it-later/ diego-research/

# 3. If step 2 fails with "pathspec did not match", the tree structure differs:
#    The ls-tree output shows full paths (e.g. diego-buenos-dias/SKILL.md) but the
#    parent directory in the tree doesn't match the filesystem layout.
#    Use the directory name from ls-tree output directly:
git -C ~/.hermes/skills checkout HEAD -- diego-buenos-dias/

# 4. Confirm restored
hermes skills list | grep -i diego

# 5. If .archive/ has copies, compare to ensure the HEAD version is canonical:
diff -r ~/.hermes/skills/.archive/diego-buenos-dias/ ~/.hermes/skills/diego-buenos-dias/
```

## Prevention — Permanent Setup

Custom skills live in `~/.hermes/custom-skills/` (git-backed, survives Hermes updates) and are symlinked into `~/.hermes/skills/`.

**Architecture:**
```
~/.hermes/custom-skills/          ← git repo, survives Hermes updates
  ├── diego-buenos-dias/
  ├── diego-read-it-later/
  ├── diego-research/
  ├── diego-intel/
  └── restore.sh                  ← recreates symlinks post-update

~/.hermes/skills/                 ← Hermes manages this; may be wiped on update
  ├── diego-buenos-dias -> ~/.hermes/custom-skills/diego-buenos-dias
  ├── diego-read-it-later -> ~/.hermes/custom-skills/diego-read-it-later
  ├── diego-research -> ~/.hermes/custom-skills/diego-research
  └── productivity/diego-intel -> ~/.hermes/custom-skills/diego-intel
```

**Post-Hermes-update recovery:**
```bash
bash ~/.hermes/custom-skills/restore.sh
```

**Adding a new custom skill:**
```bash
# 1. Place skill in custom-skills/
mv ~/.hermes/skills/new-skill ~/.hermes/custom-skills/

# 2. Create symlink
ln -s ~/.hermes/custom-skills/new-skill ~/.hermes/skills/new-skill

# 3. Commit to git backup
cd ~/.hermes/custom-skills && git add -A && git commit -m "add: new-skill"
```

**Pushing to remote backup:**
```bash
cd ~/.hermes/custom-skills
git remote add origin https://github.com/diegovelezg/dotfiles-hermes-agent.git  # first time
git branch -M main
git push -u origin main --force   # use --force if remote has divergent history
```

**Pushing to remote backup (safe — preserves remote history):**
```bash
# 1. Clone a fresh copy of the remote
git clone https://github.com/diegovelezg/dotfiles-hermes-agent.git ~/hermes-backup-new

# 2. Copy local custom-skills over
cp -r ~/.hermes/custom-skills/diego-* ~/hermes-backup-new/skills/

# 3. Commit and push
cd ~/hermes-backup-new
git config user.email "diego@hermes.local"
git config user.name "Diego"
git add -A && git commit -m "Restore custom skills" && git push

# 4. Cleanup
rm -rf ~/hermes-backup-new
```
⚠️ Never force-push to this repo — it contains full `~/.hermes/` backups (configs, cron, plugins). Force-push loses that history.

**Old prevention (deprecated):** Relying on `~/.hermes/skills/` git history alone is insufficient — Hermes Agent updates can overwrite this directory, orphaning custom skills regardless of git state.
