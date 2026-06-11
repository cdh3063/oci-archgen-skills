#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'USAGE'
Usage:
  ./install.sh --list
  ./install.sh --all [--tool codex|codex-local|codex-repo|claude]
  ./install.sh <skill-name> [--tool codex|codex-local|codex-repo|claude]

Targets:
  codex        ~/.codex/skills/<skill>       (default)
  codex-local  .codex/skills/<skill>
  codex-repo   .agents/skills/<skill>
  claude       ~/.claude/skills/<skill>
USAGE
}

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
skills_dir="$repo_dir/skills"
tool="codex"
selection=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --help|-h)
      usage
      exit 0
      ;;
    --list)
      find "$skills_dir" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort
      exit 0
      ;;
    --all)
      selection="__all__"
      shift
      ;;
    --tool)
      tool="${2:-}"
      if [[ -z "$tool" ]]; then
        echo "error: --tool requires a value" >&2
        exit 2
      fi
      shift 2
      ;;
    -*)
      echo "error: unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
    *)
      if [[ -n "$selection" ]]; then
        echo "error: multiple skill selections provided" >&2
        exit 2
      fi
      selection="$1"
      shift
      ;;
  esac
done

if [[ -z "$selection" ]]; then
  usage >&2
  exit 2
fi

case "$tool" in
  codex)
    dest_root="${CODEX_HOME:-$HOME/.codex}/skills"
    ;;
  codex-local)
    dest_root="$PWD/.codex/skills"
    ;;
  codex-repo)
    dest_root="$PWD/.agents/skills"
    ;;
  claude)
    dest_root="$HOME/.claude/skills"
    ;;
  *)
    echo "error: unsupported tool: $tool" >&2
    exit 2
    ;;
esac

install_one() {
  local name="$1"
  local src="$skills_dir/$name"
  local dest="$dest_root/$name"

  if [[ ! -d "$src" ]]; then
    echo "error: skill not found: $name" >&2
    exit 1
  fi

  mkdir -p "$dest_root"
  rm -rf "$dest"
  cp -R "$src" "$dest"
  echo "installed $name -> $dest"
}

if [[ "$selection" == "__all__" ]]; then
  while IFS= read -r skill; do
    install_one "$skill"
  done < <(find "$skills_dir" -mindepth 1 -maxdepth 1 -type d -exec basename {} \; | sort)
else
  install_one "$selection"
fi
