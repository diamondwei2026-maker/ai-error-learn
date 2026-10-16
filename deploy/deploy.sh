#!/usr/bin/env bash
#
# 错题本后端 —— 一键部署脚本（在阿里云 ECS 上执行）
#
# 完整部署步骤详见教程：.trae/documents/部署教程.md
#
# 前置条件：
#   1. 已用 git 将仓库拉到 ECS（建议 /opt/error-learn）
#   2. ECS 上已安装 python3（版本需 >=3.8）/ nginx
#      若系统 python3 过旧（如阿里云 Linux 3 的 3.6），请先装新版：
#        sudo dnf install -y python3.11 python3.11-devel
#   3. 已准备 server/.env（可先 cp deploy/env.production.example server/.env 再填值）
#   4. Nginx 站点域名与 SSL 证书已就绪（本脚本不申请证书，只安装配置）
#
# 用法：
#   sudo bash deploy/deploy.sh                 # 默认路径 /opt/error-learn、端口 8000
#   sudo DEPLOY_DIR=/opt/error-learn DOMAIN=api.example.com bash deploy/deploy.sh
#   sudo DEPLOY_DIR=/opt/error-learn DOMAIN=api.example.com PORT=8080 bash deploy/deploy.sh
#   sudo PYTHON_BIN=python3.11 bash deploy/deploy.sh     # 手动指定 Python（默认自动探测 >=3.8）
#
# 共享服务器注意：本脚本不重装 Nginx、不修改既有站点配置，仅新增站点配置并 reload，
#                 全程不会 restart Nginx，不影响服务器上已有站点。
#
set -euo pipefail

# ---- 可配置项（可用环境变量覆盖）----
DEPLOY_DIR="${DEPLOY_DIR:-/opt/error-learn}"
DOMAIN="${DOMAIN:-api.example.com}"
# 后端监听端口（共享服务器上 8000 可能被占，可改 8080 等空闲端口）
PORT="${PORT:-8000}"
# Python 解释器；留空则自动探测首个 >=3.8 的版本（如 python3.11），也可显式指定：PYTHON_BIN=python3.11
PYTHON_BIN="${PYTHON_BIN:-}"
SSL_CERT="${SSL_CERT:-/etc/nginx/ssl/${DOMAIN}.pem}"
SSL_KEY="${SSL_KEY:-/etc/nginx/ssl/${DOMAIN}.key}"
RUN_USER="${RUN_USER:-www-data}"
NGINX_CONF_D="${NGINX_CONF_D:-/etc/nginx/conf.d}"
SERVICE_NAME="error-learn-api"

log()  { printf '\033[32m[deploy]\033[0m %s\n' "$*"; }
warn() { printf '\033[33m[warn]\033[0m %s\n' "$*"; }
die()  { printf '\033[31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "请以 root 运行：sudo bash deploy/deploy.sh"
}

# 判断给定解释器是否为 Python >=3.8（本项目最低要求）
python_is_ok() {
  [ -n "$1" ] && command -v "$1" >/dev/null 2>&1 \
    && "$1" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null
}

# 自动探测首个 >=3.8 的解释器；可用 PYTHON_BIN 显式覆盖
detect_python() {
  local cand
  for cand in ${PYTHON_BIN:-} python3.12 python3.11 python3.10 python3.9 python3.8 python3; do
    if python_is_ok "${cand}"; then echo "${cand}"; return 0; fi
  done
  return 1
}

check_prereq() {
  command -v python3 >/dev/null || die "未找到 python3"
  # 本项目要求 Python >=3.8；系统 python3（如阿里云 Linux 3 的 3.6）可能过旧
  PYTHON_BIN="$(detect_python)" || die "未找到 Python >=3.8（当前 python3 为 $(python3 --version 2>&1)）。请先安装新版 Python，例如：sudo dnf install -y python3.11 python3.11-devel"
  log "使用 Python 解释器：${PYTHON_BIN}（$(${PYTHON_BIN} --version 2>&1)）"
  command -v nginx   >/dev/null || die "未找到 nginx"
  [ -d "${DEPLOY_DIR}/server" ] || die "未找到后端目录：${DEPLOY_DIR}/server（请先 git clone 仓库到 ${DEPLOY_DIR}）"
  [ -f "${DEPLOY_DIR}/server/.env" ] || die "缺少 ${DEPLOY_DIR}/server/.env，请先 cp deploy/env.production.example server/.env 并填值"
  # 端口预检：被占用则直接退出，避免装完 systemd 才失败（共享服务器上 8000 常被占）
  if ss -lnt 2>/dev/null | awk '{print $4}' | grep -qE "[:.]${PORT}$"; then
    die "端口 ${PORT} 已被占用，请改用空闲端口重跑，例如：PORT=8080 bash deploy/deploy.sh"
  fi
  [ -f "${SSL_CERT}" ] || warn "未找到证书 ${SSL_CERT}（Nginx 启动会失败，请先放置证书或用 DNS-01 签发）"
  [ -f "${SSL_KEY}" ]  || warn "未找到私钥 ${SSL_KEY}"
}

# ---- 1. 创建虚拟环境并安装依赖 ----
setup_venv() {
  log "创建/更新虚拟环境并安装依赖"
  cd "${DEPLOY_DIR}/server"
  # 已存在的 .venv 若由旧 Python（如 3.6）创建，会导致依赖装不上——自动删除重建
  if [ -d .venv ] && ! python_is_ok ./.venv/bin/python; then
    warn "现有 .venv 的 Python 过旧（$(./.venv/bin/python --version 2>&1 || echo 未知)），将重建"
    rm -rf .venv
  fi
  [ -d .venv ] || "${PYTHON_BIN}" -m venv .venv
  ./.venv/bin/python -m pip install --upgrade pip
  # PyMySQL[rsa] 提供 MySQL 8 caching_sha2_password 所需的 cryptography 依赖
  ./.venv/bin/python -m pip install -r requirements.txt
  ./.venv/bin/python -m pip install "PyMySQL[rsa]>=1.1,<2.0"
}

# ---- 2. 安装 systemd 单元 ----
setup_systemd() {
  log "安装 systemd 单元 ${SERVICE_NAME}"
  sed "s#<DEPLOY_DIR>#${DEPLOY_DIR}#g; s#User=www-data#User=${RUN_USER}#; s#Group=www-data#Group=${RUN_USER}#; s#--port 8000#--port ${PORT}#" \
    "${DEPLOY_DIR}/deploy/systemd/${SERVICE_NAME}.service" \
    > "/etc/systemd/system/${SERVICE_NAME}.service"
  systemctl daemon-reload
  systemctl enable "${SERVICE_NAME}"
  systemctl restart "${SERVICE_NAME}"
  sleep 2
  systemctl is-active --quiet "${SERVICE_NAME}" || die "服务启动失败，请查看：journalctl -u ${SERVICE_NAME} -n 50"
  log "服务已启动"
}

# ---- 3. 安装 Nginx 配置 ----
setup_nginx() {
  log "安装 Nginx 配置 error-learn.conf"
  sed "s#api.example.com#${DOMAIN}#g; s#/etc/nginx/ssl/${DOMAIN}.pem#${SSL_CERT}#g; s#/etc/nginx/ssl/${DOMAIN}.key#${SSL_KEY}#g; s#/opt/error-learn/server/uploads#${DEPLOY_DIR}/server/uploads#g; s#127.0.0.1:8000#127.0.0.1:${PORT}#g" \
    "${DEPLOY_DIR}/deploy/nginx/error-learn.conf" \
    > "${NGINX_CONF_D}/error-learn.conf"
  nginx -t || die "Nginx 配置校验失败"
  # 复用现有 Nginx 时只 reload，不 restart，避免中断其它站点
  systemctl reload nginx
  log "Nginx 已 reload"
}

# ---- 4. 健康检查 ----
health_check() {
  log "健康检查 GET /api/v1/health"
  local body
  body="$(curl -fsS --max-time 5 http://127.0.0.1:${PORT}/api/v1/health || true)"
  [ "${body}" = '{"status":"ok"}' ] || warn "本机健康检查返回异常：${body:-<空>}"
  log "本地健康检查通过：${body}"
  if curl -fsS --max-time 5 "https://${DOMAIN}/api/v1/health" >/dev/null 2>&1; then
    log "HTTPS 外部健康检查通过：https://${DOMAIN}/api/v1/health"
  else
    warn "HTTPS 外部健康检查未通过，请检查 DNS 解析 / 证书 / 微信合法域名配置"
  fi
}

main() {
  require_root
  log "部署目录：${DEPLOY_DIR}    域名：${DOMAIN}    后端端口：${PORT}"
  check_prereq
  setup_venv
  setup_systemd
  setup_nginx
  health_check
  log "完成。后续更新：git pull → pip install -r requirements.txt → systemctl restart ${SERVICE_NAME}"
}

main "$@"
