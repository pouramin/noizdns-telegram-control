from __future__ import annotations

import io
import shlex
from dataclasses import dataclass

import paramiko

from app.config import settings


class SSHExecutionError(Exception):
    pass


@dataclass
class SSHResult:
    command: str
    exit_code: int
    stdout: str
    stderr: str


class SSHRunner:
    def __init__(
        self,
        host: str,
        port: int,
        username: str,
        auth_type: str,
        password: str | None = None,
        private_key: str | None = None,
        timeout: int | None = None,
    ) -> None:
        self.host = host
        self.port = port
        self.username = username
        self.auth_type = auth_type
        self.password = password
        self.private_key = private_key
        self.timeout = timeout or settings.default_ssh_timeout
        self._client: paramiko.SSHClient | None = None

    def __enter__(self) -> "SSHRunner":
        self._client = paramiko.SSHClient()
        self._client.set_missing_host_key_policy(paramiko.AutoAddPolicy())

        connect_kwargs = {
            "hostname": self.host,
            "port": self.port,
            "username": self.username,
            "timeout": self.timeout,
            "banner_timeout": self.timeout,
            "auth_timeout": self.timeout,
        }

        if self.auth_type == "password":
            connect_kwargs["password"] = self.password
        elif self.auth_type == "private_key":
            if not self.private_key:
                raise SSHExecutionError("private_key_required")
            pkey = paramiko.RSAKey.from_private_key(io.StringIO(self.private_key))
            connect_kwargs["pkey"] = pkey
        else:
            raise SSHExecutionError("invalid_auth_type")

        self._client.connect(**connect_kwargs)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._client:
            self._client.close()

    def exec(self, command: str, sudo: bool = False) -> SSHResult:
        if not self._client:
            raise SSHExecutionError("ssh_client_not_connected")

        final_command = command
        stdin_payload = None

        if sudo and self.username != "root":
            if self.auth_type == "password" and self.password:
                final_command = f"sudo -S -p '' bash -lc {shlex.quote(command)}"
                stdin_payload = self.password + "\n"
            else:
                final_command = f"sudo bash -lc {shlex.quote(command)}"

        stdin, stdout, stderr = self._client.exec_command(final_command, timeout=self.timeout)
        if stdin_payload:
            stdin.write(stdin_payload)
            stdin.flush()

        exit_code = stdout.channel.recv_exit_status()
        out = stdout.read().decode("utf-8", errors="replace")
        err = stderr.read().decode("utf-8", errors="replace")

        return SSHResult(command=final_command, exit_code=exit_code, stdout=out, stderr=err)

    def exec_checked(self, command: str, sudo: bool = False) -> SSHResult:
        result = self.exec(command, sudo=sudo)
        if result.exit_code != 0:
            raise SSHExecutionError(
                f"command_failed\nCOMMAND: {result.command}\nEXIT_CODE: {result.exit_code}\nSTDERR:\n{result.stderr}\nSTDOUT:\n{result.stdout}"
            )
        return result
