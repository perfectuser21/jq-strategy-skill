#!/usr/bin/env bash
# jq-strategy skill 一键安装脚本
#
# 用法：
#   curl -sL https://raw.githubusercontent.com/<USER>/jq-strategy-skill/main/install.sh | bash
# 或者：
#   bash install.sh

set -euo pipefail

REPO_URL="${JQ_STRATEGY_REPO:-https://github.com/perfectuser21/jq-strategy-skill.git}"
SKILL_DIR="${HOME}/.claude/skills/jq-strategy"

say() { printf "\033[0;36m[jq-strategy]\033[0m %s\n" "$1"; }
err() { printf "\033[0;31m[jq-strategy]\033[0m %s\n" "$1" >&2; }

if ! command -v git >/dev/null 2>&1; then
    err "需要 git，请先安装"
    exit 1
fi

mkdir -p "${HOME}/.claude/skills"

if [ -d "${SKILL_DIR}" ]; then
    say "检测到已安装，执行更新..."
    cd "${SKILL_DIR}"
    git pull --ff-only
    say "✅ 更新完成：${SKILL_DIR}"
else
    say "开始安装到 ${SKILL_DIR}..."
    git clone --depth 1 "${REPO_URL}" "${SKILL_DIR}"
    say "✅ 安装完成：${SKILL_DIR}"
fi

cat <<'EOF'

下一步：
  1. 重启 Claude Code
  2. 在对话里试试：「写个策略，选市值最小的 3 只股票，每 5 天调仓」
  3. 或者：/jq-strategy <你的策略描述>

skill 会把生成的 .py 代码保存到 ~/perfect21/investment/strategies/
复制代码到 joinquant.com 即可跑回测。

EOF
