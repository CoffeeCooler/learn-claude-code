#!/usr/bin/env python3
# Harness Extension: Custom Permissions Sandbox
"""
permission_sandbox.py - 自定义权限沙箱

实现细粒度的Agent权限控制，包括：
1. 文件访问白名单/黑名单
2. 网络访问限制
3. 命令执行审批工作流
4. 信任边界管理
5. 操作审计日志
6. 权限级别系统（只读/读写/执行/管理员）

    +------------------+     +------------------+
    |  Permission     |     |   Trust Zone     |
    |  Policy Engine  |     |   Manager        |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +--------+---------+     +--------+---------+
    | Access Control |     | External Systems  |
    | List (ACL)    |     | Boundary          |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +----------------------------------------+
    |          Security Layer                 |
    |  - File whitelist/blacklist           |
    |  - Command approval workflow            |
    |  - Network isolation                   |
    |  - Operation audit log                 |
    +----------------------------------------+

扩展方向：
- 在s01_agent_loop.py中集成权限检查
- 实现更细粒度的文件级别控制
- 添加基于角色的访问控制(RBAC)
"""

import json
import os
import re
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from datetime import datetime


class PermissionLevel(Enum):
    NONE = 0
    READ_ONLY = 1
    READ_WRITE = 2
    EXECUTE = 3
    ADMIN = 4


class OperationType(Enum):
    FILE_READ = "file_read"
    FILE_WRITE = "file_write"
    FILE_DELETE = "file_delete"
    COMMAND_EXECUTE = "command_execute"
    NETWORK_ACCESS = "network_access"
    EXTERNAL_API = "external_api"
    ENV_READ = "env_read"
    ENV_WRITE = "env_write"


class RiskLevel(Enum):
    SAFE = "safe"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class PermissionRule:
    """权限规则"""
    pattern: str  # 文件路径模式或命令模式
    operation: OperationType
    allowed: bool
    risk_level: RiskLevel = RiskLevel.SAFE


@dataclass
class AccessRequest:
    """访问请求"""
    operation: OperationType
    target: str  # 文件路径、命令、网络地址等
    agent_id: str
    timestamp: float = field(default_factory=time.time)
    approved: bool = False
    approver: Optional[str] = None
    denied_reason: Optional[str] = None


@dataclass
class AuditLog:
    """审计日志"""
    id: str
    operation: OperationType
    target: str
    agent_id: str
    result: str  # approved, denied, approved_with_conditions
    risk_level: RiskLevel
    timestamp: float
    details: Dict[str, Any] = field(default_factory=dict)


class TrustBoundary:
    """信任边界管理器"""

    def __init__(self):
        self.internal_domains: Set[str] = {"localhost", "127.0.0.1"}
        self.external_trusted: Set[str] = set()
        self.blocked: Set[str] = set()
        self.api_whitelist: Set[str] = set()

    def is_internal(self, domain: str) -> bool:
        return domain in self.internal_domains

    def is_trusted(self, domain: str) -> bool:
        return domain in self.external_trusted

    def is_blocked(self, domain: str) -> bool:
        return domain in self.blocked

    def add_internal(self, domain: str):
        self.internal_domains.add(domain)

    def add_trusted(self, domain: str):
        self.external_trusted.add(domain)

    def block(self, domain: str):
        self.blocked.add(domain)


class ApprovalWorkflow:
    """审批工作流"""

    def __init__(self):
        self.pending_requests: Dict[str, AccessRequest] = {}
        self.auto_approve_safe: bool = True
        self.risk_thresholds: Dict[RiskLevel, bool] = {
            RiskLevel.SAFE: True,
            RiskLevel.LOW: True,
            RiskLevel.MEDIUM: False,
            RiskLevel.HIGH: False,
            RiskLevel.CRITICAL: False,
        }

    def request_approval(self, request: AccessRequest) -> bool:
        """请求审批"""
        risk = self.assess_risk(request)
        request.risk_level = risk

        # 根据风险等级决定是否自动批准
        if self.risk_thresholds.get(risk, False):
            request.approved = True
            request.approver = "auto"
            return True

        # 添加到待审批队列
        self.pending_requests[request.id] = request
        return False

    def approve(self, request_id: str, approver: str) -> bool:
        """审批"""
        if request_id not in self.pending_requests:
            return False
        request = self.pending_requests[request_id]
        request.approved = True
        request.approver = approver
        return True

    def deny(self, request_id: str, reason: str):
        """拒绝"""
        if request_id not in self.pending_requests:
            return False
        request = self.pending_requests[request_id]
        request.approved = False
        request.denied_reason = reason
        return True

    def assess_risk(self, request: AccessRequest) -> RiskLevel:
        """评估风险等级"""
        # 简单风险评估
        if request.operation == OperationType.COMMAND_EXECUTE:
            dangerous = ["rm -rf", "sudo", "shutdown", "curl | sh", "wget | sh"]
            if any(cmd in request.target for cmd in dangerous):
                return RiskLevel.CRITICAL
            return RiskLevel.MEDIUM

        if request.operation == OperationType.FILE_DELETE:
            return RiskLevel.HIGH

        if request.operation == OperationType.NETWORK_ACCESS:
            return RiskLevel.MEDIUM

        return RiskLevel.SAFE


class PermissionSandbox:
    """权限沙箱主类"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.rules: List[PermissionRule] = []
        self.trust_boundary = TrustBoundary()
        self.approval_workflow = ApprovalWorkflow()
        self.audit_logs: List[AuditLog] = []
        self.permission_cache: Dict[str, PermissionLevel] = {}

        self._init_default_rules()

    def _init_default_rules(self):
        """初始化默认规则"""
        # 危险命令 - 默认禁止
        dangerous_commands = [
            ("rm -rf /", OperationType.COMMAND_EXECUTE, False, RiskLevel.CRITICAL),
            ("sudo", OperationType.COMMAND_EXECUTE, False, RiskLevel.CRITICAL),
            ("shutdown", OperationType.COMMAND_EXECUTE, False, RiskLevel.CRITICAL),
            ("reboot", OperationType.COMMAND_EXECUTE, False, RiskLevel.CRITICAL),
            ("> /dev/", OperationType.COMMAND_EXECUTE, False, RiskLevel.HIGH),
        ]

        for pattern, op, allowed, risk in dangerous_commands:
            self.rules.append(PermissionRule(
                pattern=pattern,
                operation=op,
                allowed=allowed,
                risk_level=risk
            ))

    def add_rule(self, pattern: str, operation: OperationType, allowed: bool, risk: RiskLevel = RiskLevel.SAFE):
        """添加权限规则"""
        self.rules.append(PermissionRule(
            pattern=pattern,
            operation=operation,
            allowed=allowed,
            risk_level=risk
        ))

    def check_file_access(self, path: str, operation: OperationType, agent_id: str = "default") -> bool:
        """检查文件访问权限"""
        # 解析路径
        try:
            full_path = (self.workspace / path).resolve()
        except:
            return False

        # 检查是否在workspace内
        if not str(full_path).startswith(str(self.workspace.resolve())):
            audit = AuditLog(
                id=str(time.time()),
                operation=operation,
                target=path,
                agent_id=agent_id,
                result="denied",
                risk_level=RiskLevel.CRITICAL,
                timestamp=time.time(),
                details={"reason": "path escape attempt"}
            )
            self.audit_logs.append(audit)
            return False

        # 检查规则
        for rule in self.rules:
            if rule.operation == operation:
                try:
                    if re.search(rule.pattern, str(full_path)):
                        audit = AuditLog(
                            id=str(time.time()),
                            operation=operation,
                            target=path,
                            agent_id=agent_id,
                            result="approved" if rule.allowed else "denied",
                            risk_level=rule.risk_level,
                            timestamp=time.time()
                        )
                        self.audit_logs.append(audit)
                        return rule.allowed
                except:
                    pass

        # 默认允许workspace内的文件操作
        return True

    def check_command(self, command: str, agent_id: str = "default") -> bool:
        """检查命令执行权限"""
        request = AccessRequest(
            operation=OperationType.COMMAND_EXECUTE,
            target=command,
            agent_id=agent_id
        )

        # 先检查规则
        for rule in self.rules:
            if rule.operation == OperationType.COMMAND_EXECUTE:
                try:
                    if re.search(rule.pattern, command):
                        audit = AuditLog(
                            id=str(time.time()),
                            operation=OperationType.COMMAND_EXECUTE,
                            target=command,
                            agent_id=agent_id,
                            result="approved" if rule.allowed else "denied",
                            risk_level=rule.risk_level,
                            timestamp=time.time()
                        )
                        self.audit_logs.append(audit)
                        return rule.allowed
                except:
                    pass

        # 需要审批
        approved = self.approval_workflow.request_approval(request)

        audit = AuditLog(
            id=str(time.time()),
            operation=OperationType.COMMAND_EXECUTE,
            target=command,
            agent_id=agent_id,
            result="approved" if approved else "pending",
            risk_level=RiskLevel.MEDIUM,
            timestamp=time.time()
        )
        self.audit_logs.append(audit)

        return approved

    def check_network(self, url: str, agent_id: str = "default") -> bool:
        """检查网络访问权限"""
        from urllib.parse import urlparse

        try:
            parsed = urlparse(url)
            domain = parsed.netloc or parsed.path.split(":")[0]
        except:
            return False

        # 检查信任边界
        if self.trust_boundary.is_blocked(domain):
            return False

        if self.trust_boundary.is_internal(domain):
            return True

        if self.trust_boundary.is_trusted(domain):
            return True

        # 默认禁止外部网络访问
        return False

    def get_audit_logs(self, limit: int = 100) -> List[AuditLog]:
        """获取审计日志"""
        return sorted(self.audit_logs, key=lambda x: x.timestamp, reverse=True)[:limit]

    def generate_report(self) -> Dict:
        """生成安全报告"""
        total = len(self.audit_logs)
        approved = len([l for l in self.audit_logs if l.result == "approved"])
        denied = len([l for l in self.audit_logs if l.result == "denied"])

        by_operation = {}
        for log in self.audit_logs:
            op = log.operation.value
            by_operation[op] = by_operation.get(op, 0) + 1

        return {
            "total_operations": total,
            "approved": approved,
            "denied": denied,
            "approval_rate": f"{approved/total*100:.1f}%" if total > 0 else "N/A",
            "by_operation": by_operation,
            "trust_boundary": {
                "internal": list(self.trust_boundary.internal_domains),
                "trusted": list(self.trust_boundary.external_trusted),
                "blocked": list(self.trust_boundary.blocked)
            }
        }


class SandboxCommandExecutor:
    """沙箱命令执行器"""

    def __init__(self, sandbox: PermissionSandbox):
        self.sandbox = sandbox

    def execute(self, command: str, agent_id: str = "default") -> str:
        """执行命令（带权限检查）"""
        if not self.sandbox.check_command(command, agent_id):
            return "Error: Command blocked by sandbox"

        # 仍然做超时保护
        try:
            r = subprocess.run(
                command,
                shell=True,
                cwd=self.sandbox.workspace,
                capture_output=True,
                text=True,
                timeout=120
            )
            out = (r.stdout + r.stderr).strip()
            return out[:50000] if out else "(no output)"
        except subprocess.TimeoutExpired:
            return "Error: Timeout (120s)"
        except Exception as e:
            return f"Error: {e}"


class SandboxFileHandler:
    """沙箱文件处理器"""

    def __init__(self, sandbox: PermissionSandbox):
        self.sandbox = sandbox

    def read(self, path: str, agent_id: str = "default") -> str:
        """读取文件"""
        if not self.sandbox.check_file_access(path, OperationType.FILE_READ, agent_id):
            return "Error: Read permission denied"

        try:
            full_path = self.sandbox.workspace / path
            content = full_path.read_text()
            return content[:50000]
        except FileNotFoundError:
            return f"Error: File not found: {path}"
        except Exception as e:
            return f"Error: {e}"

    def write(self, path: str, content: str, agent_id: str = "default") -> str:
        """写入文件"""
        if not self.sandbox.check_file_access(path, OperationType.FILE_WRITE, agent_id):
            return "Error: Write permission denied"

        try:
            full_path = self.sandbox.workspace / path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)
            return f"Wrote {len(content)} bytes to {path}"
        except Exception as e:
            return f"Error: {e}"

    def delete(self, path: str, agent_id: str = "default") -> str:
        """删除文件"""
        if not self.sandbox.check_file_access(path, OperationType.FILE_DELETE, agent_id):
            return "Error: Delete permission denied"

        try:
            full_path = self.sandbox.workspace / path
            full_path.unlink()
            return f"Deleted {path}"
        except Exception as e:
            return f"Error: {e}"


def demo():
    """演示权限沙箱"""
    workspace = Path.cwd()

    # 创建沙箱
    sandbox = PermissionSandbox(workspace)

    # 添加自定义规则
    sandbox.add_rule(r"\.env$", OperationType.FILE_READ, True, RiskLevel.LOW)
    sandbox.add_rule(r"\.env$", OperationType.FILE_WRITE, False, RiskLevel.CRITICAL)
    sandbox.add_rule(r"\.secret$", OperationType.FILE_READ, False, RiskLevel.HIGH)

    # 设置信任边界
    sandbox.trust_boundary.add_internal("localhost")
    sandbox.trust_boundary.add_trusted("api.github.com")

    # 创建执行器
    cmd_executor = SandboxCommandExecutor(sandbox)
    file_handler = SandboxFileHandler(sandbox)

    print("=== Permission Sandbox Demo ===\n")

    # 测试命令执行
    print("1. Testing safe command:")
    result = cmd_executor.execute("ls -la")
    print(f"   'ls -la': {result[:100]}...\n")

    print("2. Testing blocked command:")
    result = cmd_executor.execute("rm -rf /")
    print(f"   'rm -rf /': {result}\n")

    # 测试文件操作
    print("3. Testing file read:")
    result = file_handler.read("README.md")
    print(f"   'README.md': {result[:100]}...\n")

    # 测试禁止的操作
    print("4. Testing .env write (should be denied):")
    result = file_handler.write(".env", "secret=key")
    print(f"   '.env': {result}\n")

    # 生成报告
    print("5. Security Report:")
    report = sandbox.generate_report()
    print(json.dumps(report, indent=2, default=str))

    print("\n[Demo completed]")


if __name__ == "__main__":
    demo()
