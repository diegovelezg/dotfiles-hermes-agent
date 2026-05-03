#!/bin/bash
# Restore custom skills symlinks after Hermes updates.
# Lives at: ~/.hermes/custom-skills/restore.sh
# Usage: bash ~/.hermes/custom-skills/restore.sh

set -e

SKILLS_DIR="$HOME/.hermes/skills"
CUSTOM_DIR="$HOME/.hermes/custom-skills"

echo "Restoring custom skills symlinks..."

# Top-level skills (diego-*)
for skill_dir in "$CUSTOM_DIR"/diego-*; do
  if [ -d "$skill_dir" ] && [ "$(basename "$skill_dir")" != "restore.sh" ]; then
    skill_name=$(basename "$skill_dir")
    link_path="$SKILLS_DIR/$skill_name"
    if [ -L "$link_path" ]; then
      echo "  $skill_name: symlink already exists"
    elif [ -d "$link_path" ]; then
      echo "  $skill_name: directory exists, skipping (manual review needed)"
    else
      mkdir -p "$(dirname "$link_path")"
      ln -sf "$skill_dir" "$link_path"
      echo "  $skill_name: symlink created"
    fi
  fi
done

# Subdirectory skills (e.g. productivity/diego-intel)
# Format in CUSTOM_DIR: <category>/<skill-name> (mirrors skills/ layout)
for category_dir in "$CUSTOM_DIR"/*/; do
  category=$(basename "$category_dir")
  for skill_dir in "$category_dir"/*; do
    if [ -d "$skill_dir" ]; then
      skill_name=$(basename "$skill_dir")
      link_path="$SKILLS_DIR/$category/$skill_name"
      if [ -L "$link_path" ]; then
        echo "  $category/$skill_name: symlink already exists"
      elif [ -d "$link_path" ]; then
        echo "  $category/$skill_name: directory exists, skipping"
      else
        mkdir -p "$SKILLS_DIR/$category"
        ln -sf "$skill_dir" "$link_path"
        echo "  $category/$skill_name: symlink created"
      fi
    fi
  done
done

# Sync git backup (commit any uncommitted changes)
if [ -d "$CUSTOM_DIR/.git" ]; then
  echo "Syncing git backup..."
  cd "$CUSTOM_DIR"
  if [ -n "$(git status --porcelain)" ]; then
    git add -A
    git commit -m "Update: $(date -Iseconds)" 2>/dev/null || true
    echo "  git commit done"
  else
    echo "  nothing to commit"
  fi
fi

echo "Done."
