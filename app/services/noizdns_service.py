from __future__ import annotations

import shlex

from app.config import settings
from app.models import Server
from app.services.server_service import resolved_secret
from app.ssh import SSHRunner


def _runner_for(server: Server) -> SSHRunner:
    password, private_key = resolved_secret(server)
    return SSHRunner(
        host=server.host,
        port=server.port,
        username=server.username,
        auth_type=server.auth_type,
        password=password,
        private_key=private_key,
    )


def install_noizdns(server: Server) -> str:
    repo_url = shlex.quote(settings.git_repo_url)
    branch = shlex.quote(settings.git_branch)
    domain = shlex.quote(server.noizdns_domain)
    mtu = server.noizdns_mtu

    command = f"""
set -e
if [ ! -d "$HOME/noizdns-deploy" ]; then
  git clone {repo_url} "$HOME/noizdns-deploy"
fi
cd "$HOME/noizdns-deploy"
git fetch origin
git checkout {branch}
git pull --ff-only origin {branch}
bash ./noizdns-deploy.sh --domain {domain} --mtu {mtu}
""".strip()

    with _runner_for(server) as runner:
        result = runner.exec_checked(command, sudo=True)
    return result.stdout.strip() or "Install completed."


def status(server: Server) -> str:
    with _runner_for(server) as runner:
        result = runner.exec_checked("noizdns-admin status", sudo=True)
    return result.stdout.strip()


def config_show(server: Server) -> str:
    with _runner_for(server) as runner:
        result = runner.exec_checked("noizdns-admin config show", sudo=True)
    return result.stdout.strip()


def service_action(server: Server, action: str) -> str:
    if action not in {"start", "stop", "restart"}:
        raise ValueError("invalid_service_action")
    with _runner_for(server) as runner:
        result = runner.exec_checked(f"noizdns-admin service {action}", sudo=True)
    return result.stdout.strip()


def logs(server: Server, lines: int = 100) -> str:
    with _runner_for(server) as runner:
        result = runner.exec_checked(f"noizdns-admin logs --lines {int(lines)}", sudo=True)
    return result.stdout.strip()


def users_list(server: Server) -> str:
    with _runner_for(server) as runner:
        result = runner.exec_checked("noizdns-admin users list", sudo=True)
    return result.stdout.strip()


def users_add(server: Server, username: str, password: str) -> str:
    with _runner_for(server) as runner:
        cmd = f"noizdns-admin users add --username {shlex.quote(username)} --password {shlex.quote(password)}"
        result = runner.exec_checked(cmd, sudo=True)
    return result.stdout.strip()


def users_remove(server: Server, username: str) -> str:
    with _runner_for(server) as runner:
        cmd = f"noizdns-admin users remove --username {shlex.quote(username)}"
        result = runner.exec_checked(cmd, sudo=True)
    return result.stdout.strip()


def users_passwd(server: Server, username: str, password: str) -> str:
    with _runner_for(server) as runner:
        cmd = f"noizdns-admin users passwd --username {shlex.quote(username)} --password {shlex.quote(password)}"
        result = runner.exec_checked(cmd, sudo=True)
    return result.stdout.strip()
