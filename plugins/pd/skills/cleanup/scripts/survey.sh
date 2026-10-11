#!/usr/bin/env bash
# Read-only survey of every worktree and stray local branch.
# usage: survey.sh [path]   default: current directory
#   inside a repo      -> survey that repo
#   anywhere else      -> find every repo under <path> (drive root, folder of projects) and survey each
# Fetches (with prune) first; changes nothing else. Column meanings: references/classification.md.
set -u
root=$(cd "${1:-.}" && pwd) || exit 2
now=$(date +%s)

echo "free space: $(df -h "$root" | tail -1 | awk '{print $4" of "$2" ("$5" used)"}')"

pr_of() {  # "#12 MERGED,#9 CLOSED" or "none"
  local s; s=$(awk -F'\t' -v b="$1" '$1==b {print $2}' <<<"$prs" | paste -sd, -)
  echo "${s:-none}"
}
pr_head() {  # same | DIFF | -  (local tip vs head of the merged PR)
  local oids; oids=$(awk -F'\t' -v b="$1" '$1==b && $3=="MERGED" {print $4}' <<<"$prs")
  [ -z "$oids" ] && { echo -; return; }
  grep -qx "$2" <<<"$oids" && echo same || echo DIFF
}
idle() {  # time since newest of: HEAD move, HEAD commit, dirty-file edit
  local t
  t=$( { git log -1 --format=%ct HEAD
         stat -c %Y "$(git rev-parse --absolute-git-dir)/logs/HEAD" 2>/dev/null
         git ls-files -z -m -o --exclude-standard | head -z -n 500 | xargs -0 -r stat -c %Y 2>/dev/null
       } | sort -n | tail -1)
  local h=$(( (now - ${t:-0}) / 3600 ))
  [ "$h" -lt 48 ] && echo "${h}h" || echo "$(( h / 24 ))d"
}
size_gb() { du -sk "$1" 2>/dev/null | awk '{printf "%.1f", $1/1048576}'; }

survey_one() {  # cwd = a repo
  local here base first dirty_list wt_branches path sha branch flags role dirty ahead ref remote pr ph b up track p n
  here=$(git rev-parse --show-toplevel)
  echo; echo "=== repo: $here"
  git fetch --prune --quiet origin || echo "WARN: fetch failed, remote data may be stale"
  base=$(git symbolic-ref --short refs/remotes/origin/HEAD 2>/dev/null || echo origin/main)
  prs=$(gh pr list --state all --limit 1000 --json headRefName,number,state,headRefOid \
    --jq '.[] | [.headRefName, "#\(.number) \(.state)", .state, .headRefOid] | @tsv' 2>/dev/null) \
    || { echo "WARN: gh pr list failed, PR column is empty"; prs=; }

  echo "local main vs $base (ahead behind): $(git rev-list --left-right --count main..."$base" 2>/dev/null || echo n/a)"
  printf 'path\tref\tsize_gb\tdirty\tahead\tremote\tpr\tpr_head\tidle\tflags\n'
  first=1; dirty_list=(); wt_branches=()
  # \037 (unit separator), not tab: read collapses empty tab fields (detached has no branch)
  while IFS=$'\037' read -r path sha branch flags; do
    role=""; [ $first = 1 ] && role="MAIN"; [ "$path" = "$here" ] && role="${role:+$role,}CURRENT"
    first=0
    if [ ! -d "$path" ]; then
      printf '%s\t%s\t-\t-\t-\t-\t-\t-\t-\tmissing %s\n' "$path" "${branch:-detached}" "$flags"; continue
    fi
    [ -n "$branch" ] && wt_branches+=("$branch")
    dirty=$(cd "$path" && git status --porcelain | wc -l)
    [ "$dirty" -gt 0 ] && [ -z "$role" ] && dirty_list+=("$path")
    ahead=$(git rev-list --count "$base..$sha")
    if [ -n "$branch" ]; then
      ref=$branch
      git rev-parse -q --verify "refs/remotes/origin/$branch" >/dev/null && remote=yes || remote=no
      pr=$(pr_of "$branch"); ph=$(pr_head "$branch" "$sha")
    else
      ref="detached:${sha:0:8}"
      [ -n "$(git for-each-ref --contains "$sha" --count=1)" ] && remote=reachable || remote=orphan
      pr=-; ph=-
    fi
    printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$path" "$ref" "$(size_gb "$path")" "$dirty" "$ahead" "$remote" "$pr" "$ph" \
      "$(cd "$path" && idle)" "${role} ${flags}"
  done < <(git worktree list --porcelain | awk -v OFS='\037' '
    /^worktree /{p=substr($0,10); b=""; f=""}
    /^HEAD /{h=$2}
    /^branch /{b=substr($2,12)}
    /^locked/{f=f" locked"}
    /^prunable/{f=f" prunable"}
    /^$/{print p, h, b, f}')

  echo "== local branches without a worktree (branch, track, ahead, pr, pr_head)"
  git for-each-ref --format='%(refname:short)%1f%(upstream)%1f%(upstream:track)%1f%(objectname)' refs/heads |
  while IFS=$'\037' read -r b up track sha; do
    [ "$b" = "main" ] || [ "$b" = "master" ] && continue
    printf '%s\n' "${wt_branches[@]}" | grep -qx "$b" && continue
    [ -z "$up" ] && track="[no upstream]"
    printf '%s\t%s\t%s\t%s\t%s\n' "$b" "${track:-[in sync]}" "$(git rev-list --count "$base..$sha")" \
      "$(pr_of "$b")" "$(pr_head "$b" "$sha")"
  done

  for p in "${dirty_list[@]}"; do
    echo "== dirty: $p"
    (cd "$p" && git status --porcelain | head -20
     n=$(git status --porcelain | wc -l); [ "$n" -gt 20 ] && echo "... +$((n - 20)) more"
     git diff --quiet --ignore-cr-at-eol 2>/dev/null && [ -n "$(git diff --name-only)" ] && echo "(tracked changes are line-endings only)")
  done
}

if (cd "$root" && git rev-parse --show-toplevel >/dev/null 2>&1); then
  (cd "$root" && survey_one)
else
  echo "not a repo: scanning $root for repos (this can take a minute)"
  # .git DIRECTORIES are repos; a worktree's .git is a file and is reached through its repo's `git worktree list`
  find "$root" -maxdepth 7 \( -name node_modules -o -name '$RECYCLE.BIN' -o -name 'System Volume Information' \) -prune \
    -o -type d -name .git -print -prune 2>/dev/null | sort | while read -r g; do
    (cd "${g%/.git}" && survey_one)
  done
fi
