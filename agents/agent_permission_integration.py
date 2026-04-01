#!/usr/bin/env python3
# Harness Extension: Agent Permission Integration
"""
agent_permission_integration.py - Agent权限集成

将Permission Sandbox与Multi-Agent系统深度集成：
1. 每个Agent独立的权限作用域
2. 基于角色的访问控制 (RBAC)
3. Agent能力与权限自动映射
4. 跨Agent资源访问控制
5. 权限委托机制

    +------------------+     +------------------+
    |  Agent          |     |  Permission     |
    |  Registry       |     |  Policy Engine  |
    +--------+---------+     +--------+---------+
              |                        |
              v                        v
    +--------+---------+     +--------+---------+
    | Agent Scope   |     | RBAC Rules     |
    | Manager      |     | (Role-Based)   |
    +--------+---------+     +--------+---------+
              |                        |
              v                        v
    +----------------------------------------+
    |       Permission Enforcement            |
    |  - File access control                  |
    |  - Command approval                     |
    |  - Network restrictions                 |
    +----------------------------------------+

扩展方向：
- 与workflow_engine集成实现阶段权限
- 实现权限继承与委托
- 添加审计追踪
"""

import json
import os
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


class AgentRole(Enum):
    """Agent角色"""
    OBSERVER = "observer"      # 只读观察者
    DEVELOPER = "developer"     # 开发者
    REVIEWER = "reviewer"       # 审查者
    TESTER = "tester"           # 测试人员
    DEPLOYER = "deployer"       # 部署人员
    ADMIN = "admin"             # 管理员


class ResourceType(Enum):
    """资源类型"""
    FILE = "file"
    DIRECTORY = "directory"
    COMMAND = "command"
    NETWORK = "network"
    ENVIRONMENT = "environment"
    SECRET = "secret"


@dataclass
class PermissionScope:
    """权限作用域"""
    agent_id: str
    allowed_paths: Set[str] = field(default_factory=set)
    denied_paths: Set[str] = field(default_factory=set)
    allowed_commands: Set[str] = field(default_factory=set)
    denied_commands: Set[str] = field(default_factory=set)
    allowed_networks: Set[str] = field(default_factory=set)
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    can_execute_shell: bool = False
    can_access_secrets: bool = False


@dataclass
class RBACRule:
    """RBAC规则"""
    role: AgentRole
    resource_type: ResourceType
    permission: str  # read, write, execute
    pattern: str  # 正则匹配
    conditions: Optional[Callable] = None


@dataclass
class AccessContext:
    """访问上下文"""
    agent_id: str
    role: AgentRole
    task_id: Optional[str]
    workflow_stage: Optional[str]
    resources_requested: List[str]
    timestamp: float = field(default_factory=time.time)


class RolePermissionMapper:
    """角色权限映射器"""

    # 角色默认权限配置
    DEFAULT_ROLE_PERMISSIONS = {
        AgentRole.OBSERVER: {
            "files": {
                "allowed_patterns": [r".*\.md$", r".*\.txt$", r".*README.*"],
                "denied_patterns": [r".*\.env.*", r".*\.secret.*", r".*\.key.*"],
                "max_size": 1024 * 1024,  # 1MB
            },
            "commands": {
                "allowed": ["ls", "cat", "grep", "find"],
                "denied": ["rm", "mv", "cp", "chmod", "sudo"],
            },
            "networks": {
                "allowed": [],
                "denied": ["*"],
            }
        },
        AgentRole.DEVELOPER: {
            "files": {
                "allowed_patterns": [r".*\.py$", r".*\.js$", r".*\.ts$", r".*\.json$", r".*\.md$"],
                "denied_patterns": [r".*\.env.*", r".*\.secret.*", r".*config/prod.*"],
                "max_size": 10 * 1024 * 1024,  # 10MB
            },
            "commands": {
                "allowed": ["python", "node", "npm", "git", "ls", "cat", "grep"],
                "denied": ["rm -rf", "sudo", "shutdown", "reboot"],
            },
            "networks": {
                "allowed": ["localhost", "127.0.0.1", "api.github.com"],
                "denied": [],
            }
        },
        AgentRole.REVIEWER: {
            "files": {
                "allowed_patterns": [r".*"],
                "denied_patterns": [r".*\.env.*", r".*\.secret.*", r".*\.key.*"],
                "max_size": 50 * 1024 * 1024,  # 50MB
            },
            "commands": {
                "allowed": ["git", "grep", "find", "diff"],
                "denied": ["rm", "mv", "cp", "chmod"],
            },
            "networks": {
                "allowed": ["localhost", "127.0.0.1"],
                "denied": [],
            }
        },
        AgentRole.TESTER: {
            "files": {
                "allowed_patterns": [r".*\.py$", r".*\.js$", r".*\.ts$", r".*test.*", r".*spec.*"],
                "denied_patterns": [r".*\.env.*", r".*\.secret.*"],
                "max_size": 10 * 1024 * 1024,
            },
            "commands": {
                "allowed": ["python", "pytest", "npm", "node", "git"],
                "denied": ["rm -rf", "sudo", "shutdown"],
            },
            "networks": {
                "allowed": ["localhost", "127.0.0.1"],
                "denied": [],
            }
        },
        AgentRole.DEPLOYER: {
            "files": {
                "allowed_patterns": [r".*", r"Dockerfile", r".*config.*"],
                "denied_patterns": [r".*\.env.*production.*"],
                "max_size": 100 * 1024 * 1024,
            },
            "commands": {
                "allowed": ["docker", "kubectl", "python", "npm"],
                "denied": ["rm -rf /", "shutdown"],
            },
            "networks": {
                "allowed": ["*"],
                "denied": [],
            }
        },
        AgentRole.ADMIN: {
            "files": {
                "allowed_patterns": [r".*"],
                "denied_patterns": [],
                "max_size": 500 * 1024 * 1024,
            },
            "commands": {
                "allowed": ["*"],
                "denied": [],
            },
            "networks": {
                "allowed": ["*"],
                "denied": [],
            }
        },
    }

    @classmethod
    def get_permissions_for_role(cls, role: AgentRole) -> Dict:
        """获取角色的默认权限"""
        return cls.DEFAULT_ROLE_PERMISSIONS.get(role, {})


class AgentScopeManager:
    """Agent作用域管理器"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.scopes: Dict[str, PermissionScope] = {}
        self.role_map: Dict[str, AgentRole] = {}
        self.delegations: Dict[str, Dict[str, Any]] = {}  # agent_id -> delegated permissions

    def create_scope(
        self,
        agent_id: str,
        role: AgentRole,
        custom_rules: Dict = None
    ) -> PermissionScope:
        """为Agent创建权限作用域"""
        role_permissions = RolePermissionMapper.get_permissions_for_role(role)
        
        if custom_rules:
            # 合并自定义规则
            role_permissions = self._merge_rules(role_permissions, custom_rules)

        # 构建路径模式
        allowed_paths = set()
        denied_paths = set()
        
        for pattern in role_permissions.get("files", {}).get("allowed_patterns", []):
            allowed_paths.add(pattern)
        
        for pattern in role_permissions.get("files", {}).get("denied_patterns", []):
            denied_paths.add(pattern)

        # 构建命令模式
        allowed_commands = set(role_permissions.get("commands", {}).get("allowed", []))
        denied_commands = set(role_permissions.get("commands", {}).get("denied", []))

        # 构建网络规则
        allowed_networks = set(role_permissions.get("networks", {}).get("allowed", []))
        
        scope = PermissionScope(
            agent_id=agent_id,
            allowed_paths=allowed_paths,
            denied_paths=denied_paths,
            allowed_commands=allowed_commands,
            denied_commands=denied_commands,
            allowed_networks=allowed_networks,
            max_file_size=role_permissions.get("files", {}).get("max_size", 10 * 1024 * 1024),
            can_execute_shell="shell" in allowed_commands or "*" in allowed_commands,
            can_access_secrets=role == AgentRole.ADMIN
        )

        self.scopes[agent_id] = scope
        self.role_map[agent_id] = role

        return scope

    def _merge_rules(self, base: Dict, custom: Dict) -> Dict:
        """合并规则"""
        result = base.copy()
        for key, value in custom.items():
            if key in result and isinstance(value, dict):
                result[key] = self._merge_rules(result[key], value)
            else:
                result[key] = value
        return result

    def get_scope(self, agent_id: str) -> Optional[PermissionScope]:
        """获取Agent作用域"""
        return self.scopes.get(agent_id)

    def get_role(self, agent_id: str) -> Optional[AgentRole]:
        """获取Agent角色"""
        return self.role_map.get(agent_id)

    def delegate_permission(
        self,
        from_agent: str,
        to_agent: str,
        permissions: Dict[str, Any],
        duration: float = 3600.0
    ):
        """委托权限"""
        delegation = {
            "from": from_agent,
            "permissions": permissions,
            "expires_at": time.time() + duration
        }
        self.delegations[to_agent] = delegation

    def check_delegation(self, agent_id: str) -> Optional[Dict]:
        """检查委托是否有效"""
        delegation = self.delegations.get(agent_id)
        if delegation and delegation["expires_at"] > time.time():
            return delegation
        return None


class AgentPermissionEnforcer:
    """Agent权限执行器"""

    def __init__(self, scope_manager: AgentScopeManager):
        self.scope_manager = scope_manager
        self.access_log: List[Dict] = []

    def check_file_access(
        self,
        agent_id: str,
        operation: str,  # read, write, delete
        file_path: str
    ) -> tuple[bool, str]:
        """检查文件访问权限"""
        scope = self.scope_manager.get_scope(agent_id)
        if not scope:
            return True, "No scope defined, allowing"

        # 检查是否在denied列表中
        for pattern in scope.denied_paths:
            if re.search(pattern, file_path):
                self._log_access(agent_id, "file", operation, file_path, False, "Denied by pattern")
                return False, f"Access denied: matches denied pattern {pattern}"

        # 检查是否在allowed列表中
        for pattern in scope.allowed_paths:
            if re.search(pattern, file_path):
                self._log_access(agent_id, "file", operation, file_path, True, "Allowed by pattern")
                return True, "Access granted"

        # 检查默认规则
        if not scope.allowed_paths:
            # 无限制
            return True, "No restrictions"

        self._log_access(agent_id, "file", operation, file_path, False, "No matching pattern")
        return False, "Access denied: no matching allowed pattern"

    def check_command(
        self,
        agent_id: str,
        command: str
    ) -> tuple[bool, str]:
        """检查命令执行权限"""
        scope = self.scope_manager.get_scope(agent_id)
        if not scope:
            return True, "No scope defined, allowing"

        # 检查是否被禁止
        for denied in scope.denied_commands:
            if denied in command or denied == "*":
                self._log_access(agent_id, "command", "execute", command, False, f"Denied: {denied}")
                return False, f"Command denied: matches denied pattern {denied}"

        # 检查是否被允许
        for allowed in scope.allowed_commands:
            if allowed in command or allowed == "*":
                self._log_access(agent_id, "command", "execute", command, True, "Allowed")
                return True, "Command allowed"

        # 无权限执行shell
        if not scope.can_execute_shell:
            self._log_access(agent_id, "command", "execute", command, False, "Shell not allowed")
            return False, "Shell execution not allowed for this role"

        return False, "No matching command pattern"

    def check_network(
        self,
        agent_id: str,
        url: str
    ) -> tuple[bool, str]:
        """检查网络访问权限"""
        scope = self.scope_manager.get_scope(agent_id)
        if not scope:
            return True, "No scope defined, allowing"

        from urllib.parse import urlparse
        try:
            parsed = urlparse(url if "://" in url else f"http://{url}")
            domain = parsed.netloc or parsed.path.split(":")[0]
        except:
            return False, "Invalid URL"

        # 检查黑名单
        if domain in scope.denied_paths or "*" in scope.denied_paths:
            self._log_access(agent_id, "network", "access", url, False, "Domain blocked")
            return False, "Network access denied"

        # 检查白名单
        if domain in scope.allowed_networks or "*" in scope.allowed_networks:
            self._log_access(agent_id, "network", "access", url, True, "Domain allowed")
            return True, "Network access allowed"

        return False, "Network not in allowed list"

    def check_file_size(
        self,
        agent_id: str,
        file_size: int
    ) -> tuple[bool, str]:
        """检查文件大小"""
        scope = self.scope_manager.get_scope(agent_id)
        if not scope:
            return True, "No scope defined"

        if file_size > scope.max_file_size:
            return False, f"File size {file_size} exceeds limit {scope.max_file_size}"

        return True, "File size OK"

    def _log_access(
        self,
        agent_id: str,
        resource_type: str,
        operation: str,
        resource: str,
        granted: bool,
        reason: str
    ):
        """记录访问日志"""
        self.access_log.append({
            "agent_id": agent_id,
            "resource_type": resource_type,
            "operation": operation,
            "resource": resource,
            "granted": granted,
            "reason": reason,
            "timestamp": time.time()
        })

    def get_access_log(self, agent_id: str = None, limit: int = 100) -> List[Dict]:
        """获取访问日志"""
        logs = self.access_log
        if agent_id:
            logs = [l for l in logs if l["agent_id"] == agent_id]
        return logs[-limit:]


class IntegratedAgentPermissionSystem:
    """集成Agent权限系统"""

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.scope_manager = AgentScopeManager(workspace)
        self.enforcer = AgentPermissionEnforcer(self.scope_manager)

        # 默认角色
        self.role_defaults = {
            "observer": AgentRole.OBSERVER,
            "developer": AgentRole.DEVELOPER,
            "reviewer": AgentRole.REVIEWER,
            "tester": AgentRole.TESTER,
            "deployer": AgentRole.DEPLOYER,
            "admin": AgentRole.ADMIN,
        }

    def register_agent(
        self,
        agent_id: str,
        role: str,
        custom_rules: Dict = None
    ) -> bool:
        """注册Agent并创建权限作用域"""
        agent_role = self.role_defaults.get(role, AgentRole.DEVELOPER)
        
        if isinstance(role, str):
            try:
                agent_role = AgentRole(role)
            except:
                agent_role = AgentRole.DEVELOPER

        self.scope_manager.create_scope(agent_id, agent_role, custom_rules)
        
        print(f"[PermissionSystem] Registered {agent_id} with role {agent_role.value}")
        return True

    def check_access(
        self,
        agent_id: str,
        access_type: str,  # file, command, network
        operation: str,
        resource: str
    ) -> tuple[bool, str]:
        """检查访问权限"""
        if access_type == "file":
            return self.enforcer.check_file_access(agent_id, operation, resource)
        elif access_type == "command":
            return self.enforcer.check_command(agent_id, resource)
        elif access_type == "network":
            return self.enforcer.check_network(agent_id, resource)
        
        return False, "Unknown access type"

    def get_agent_permissions(self, agent_id: str) -> Dict:
        """获取Agent权限信息"""
        scope = self.scope_manager.get_scope(agent_id)
        role = self.scope_manager.get_role(agent_id)
        
        if not scope:
            return {}

        return {
            "agent_id": agent_id,
            "role": role.value if role else "unknown",
            "allowed_files": list(scope.allowed_paths),
            "denied_files": list(scope.denied_paths),
            "allowed_commands": list(scope.allowed_commands),
            "denied_commands": list(scope.denied_commands),
            "allowed_networks": list(scope.allowed_networks),
            "max_file_size": scope.max_file_size,
            "can_execute_shell": scope.can_execute_shell,
            "can_access_secrets": scope.can_access_secrets
        }

    def get_audit_report(self) -> Dict:
        """获取审计报告"""
        logs = self.enforcer.access_log
        total = len(logs)
        granted = len([l for l in logs if l["granted"]])
        denied = total - granted

        by_agent = defaultdict(lambda: {"total": 0, "granted": 0, "denied": 0})
        for log in logs:
            by_agent[log["agent_id"]]["total"] += 1
            if log["granted"]:
                by_agent[log["agent_id"]]["granted"] += 1
            else:
                by_agent[log["agent_id"]]["denied"] += 1

        return {
            "total_accesses": total,
            "granted": granted,
            "denied": denied,
            "grant_rate": f"{granted/total*100:.1f}%" if total > 0 else "N/A",
            "by_agent": dict(by_agent)
        }


def demo():
    """演示Agent权限集成"""
    workspace = Path.cwd()

    print("=== Agent Permission Integration Demo ===\n")

    # 创建权限系统
    ps = IntegratedAgentPermissionSystem(workspace)

    # 注册不同角色的Agent
    print("1. Registering agents with different roles:")
    ps.register_agent("alice", "developer")
    ps.register_agent("bob", "reviewer")
    ps.register_agent("charlie", "tester")
    ps.register_agent("dave", "deployer")
    ps.register_agent("admin", "admin")

    # 查看权限
    print("\n2. Agent permissions:")
    for agent_id in ["alice", "bob", "charlie", "dave", "admin"]:
        perms = ps.get_agent_permissions(agent_id)
        print(f"   {agent_id} ({perms.get('role')}):")
        print(f"      Files: {len(perms.get('allowed_files', []))} allowed patterns")
        print(f"      Commands: {len(perms.get('allowed_commands', []))} allowed")

    # 测试访问控制
    print("\n3. Testing access control:")

    test_cases = [
        ("alice", "command", "execute", "python main.py"),
        ("alice", "command", "execute", "rm -rf /"),
        ("bob", "file", "read", "src/main.py"),
        ("bob", "file", "read", ".env"),
        ("charlie", "file", "write", "tests/test_auth.py"),
        ("admin", "file", "read", ".env"),
        ("alice", "network", "access", "api.github.com"),
        ("alice", "network", "access", "evil.com"),
    ]

    for agent_id, atype, op, resource in test_cases:
        granted, reason = ps.check_access(agent_id, atype, op, resource)
        status = "✓" if granted else "✗"
        print(f"   {status} {agent_id} {op} {resource}: {reason}")

    # 审计报告
    print("\n4. Audit report:")
    report = ps.get_audit_report()
    print(f"   Total accesses: {report['total_accesses']}")
    print(f"   Granted: {report['granted']}")
    print(f"   Denied: {report['denied']}")
    print(f"   Grant rate: {report['grant_rate']}")

    print("\n[Demo completed]")


if __name__ == "__main__":
    demo()
