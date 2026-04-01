#!/usr/bin/env python3
# Harness Extension: Integrated Agent Harness
"""
integrated_harness.py - 集成Agent Harness

整合所有扩展模块的统一Harness：
1. Multi-Agent协作 (s09_extended_multi_agent.py)
2. Permission Sandbox (permission_sandbox.py)
3. Distributed Coordinator (distributed_agent_coordinator.py)
4. RAG Context (rag_enhanced_context.py)
5. Workflow Engine (workflow_engine.py)

    +--------------------------------------------------+
    |              Integrated Harness                    |
    |  +--------------------------------------------+  |
    |  |           Core Agent Loop                 |  |
    |  +--------------------------------------------+  |
    |           |         |         |         |      |
    |           v         v         v         v      |
    |  +-----------+ +-----------+ +-----------+   |
    |  | Multi-   | | Permission| | Workflow  |   |
    |  | Agent     | | Sandbox   | | Engine    |   |
    |  +-----------+ +-----------+ +-----------+   |
    |           |         |         |         |      |
    |           v         v         v         v      |
    |  +-------------------------------------------+  |
    |  |     Distributed Coordinator               |  |
    |  |  (Task Registry + Node Registry + RAG) |  |
    |  +-------------------------------------------+  |
    +--------------------------------------------------+

使用方式：
    harness = IntegratedHarness(project_root)
    harness.register_agent("coder", skills=["python"])
    harness.run_task("Build auth system")
"""

import json
import os
import subprocess
import threading
import time
import uuid
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

# 导入所有扩展模块
try:
    from s09_extended_multi_agent import (
        MultiAgentHarness, AgentRegistry, AgentCapability, Task, TaskStatus,
        MessageBus, DistributionStrategy, AgentMessage, MessageType
    )
    from permission_sandbox import (
        PermissionSandbox, SandboxCommandExecutor, SandboxFileHandler,
        OperationType, RiskLevel, PermissionLevel
    )
    from distributed_agent_coordinator import (
        DistributedCoordinator, DistributedTask, TaskState
    )
    from rag_enhanced_context import (
        RAGContextManager, SimpleVectorStore
    )
    from workflow_engine import (
        IntegratedWorkflowEngine, WorkflowExecutor, create_code_review_workflow
    )
    EXTENSIONS_AVAILABLE = True
except ImportError as e:
    print(f"[Warning] Some extensions not available: {e}")
    EXTENSIONS_AVAILABLE = False


class HarnessMode(Enum):
    LOCAL = "local"  # 本地单Agent
    MULTI_AGENT = "multi_agent"  # 多Agent协作
    DISTRIBUTED = "distributed"  # 分布式
    WORKFLOW = "workflow"  # 工作流模式


@dataclass
class AgentConfig:
    """Agent配置"""
    agent_id: str
    skills: List[str]
    specialty: List[str] = field(default_factory=list)
    max_concurrent: int = 2
    permission_level: str = "read_only"  # read_only, read_write, execute, admin


@dataclass
class TaskRequest:
    """任务请求"""
    task_id: str
    description: str
    required_skills: List[str]
    priority: int = 5
    mode: HarnessMode = HarnessMode.LOCAL
    workflow_template: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务结果"""
    task_id: str
    status: str
    result: Any
    agent_id: Optional[str]
    duration: float
    artifacts: Dict = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)


class IntegratedHarness:
    """
    集成Harness主类
    
    提供统一的接口来使用所有扩展功能：
    - 多Agent协作
    - 权限控制
    - 分布式支持
    - RAG知识增强
    - 工作流编排
    """

    def __init__(
        self,
        project_root: Path,
        mode: HarnessMode = HarnessMode.LOCAL
    ):
        self.project_root = project_root
        self.mode = mode
        self.agent_configs: Dict[str, AgentConfig] = {}
        self.task_history: List[TaskResult] = []

        # 初始化各组件
        self._init_components()

    def _init_components(self):
        """初始化组件"""
        if not EXTENSIONS_AVAILABLE:
            print("[Warning] Running in limited mode - extensions not available")
            return

        # 1. Permission Sandbox
        self.sandbox = PermissionSandbox(self.project_root)
        self.cmd_executor = SandboxCommandExecutor(self.sandbox)
        self.file_handler = SandboxFileHandler(self.sandbox)

        # 2. Multi-Agent Harness
        self.multi_agent = MultiAgentHarness(
            self.project_root,
            DistributionStrategy.BEST_MATCH
        )

        # 3. RAG Context Manager
        self.rag = RAGContextManager(self.project_root)

        # 4. Workflow Engine
        self.workflow_engine = IntegratedWorkflowEngine(self.project_root)

        # 5. Distributed Coordinator (可选)
        self.distributed: Optional[DistributedCoordinator] = None

        print(f"[IntegratedHarness] Initialized in {self.mode.value} mode")

    def set_mode(self, mode: HarnessMode):
        """切换模式"""
        self.mode = mode
        print(f"[IntegratedHarness] Switched to {mode.value} mode")

    # ============ Agent Management ============

    def register_agent(
        self,
        agent_id: str,
        skills: List[str],
        specialty: List[str] = None,
        permission_level: str = "read_only"
    ):
        """注册Agent"""
        config = AgentConfig(
            agent_id=agent_id,
            skills=skills,
            specialty=specialty or [],
            permission_level=permission_level
        )
        self.agent_configs[agent_id] = config

        # 注册到多Agent系统
        if EXTENSIONS_AVAILABLE:
            self.multi_agent.register_agent(agent_id, skills, specialty)

            # 设置权限
            self._apply_agent_permissions(agent_id, permission_level)

        print(f"[IntegratedHarness] Registered agent: {agent_id} ({permission_level})")

    def _apply_agent_permissions(self, agent_id: str, level: str):
        """应用Agent权限"""
        # 根据权限级别配置沙箱规则
        if level == "read_only":
            # 只读Agent只能读取文件
            pass
        elif level == "read_write":
            # 读写Agent可以修改文件
            pass
        elif level == "execute":
            # 执行Agent可以运行命令
            pass
        elif level == "admin":
            # 管理员Agent有完全权限
            pass

    # ============ Task Execution ============

    def run_task(
        self,
        description: str,
        required_skills: List[str] = None,
        priority: int = 5,
        context: Dict = None,
        use_rag: bool = True,
        use_workflow: bool = False,
        workflow_template: str = None
    ) -> TaskResult:
        """运行任务"""
        task_id = f"task_{uuid.uuid4().hex[:8]}"
        required_skills = required_skills or []
        start_time = time.time()

        print(f"\n[IntegratedHarness] Running task: {description[:50]}...")

        try:
            # 1. 获取增强上下文 (RAG)
            messages = []
            if use_rag and EXTENSIONS_AVAILABLE:
                history = context.get("history", []) if context else []
                system_prompt = context.get("system_prompt") if context else None
                messages = self.rag.get_context(description, history, system_prompt)

            # 2. 选择执行模式
            if use_workflow and workflow_template and EXTENSIONS_AVAILABLE:
                result = self._run_workflow_task(
                    task_id, description, required_skills, workflow_template, context
                )
            elif self.mode == HarnessMode.DISTRIBUTED and EXTENSIONS_AVAILABLE:
                result = self._run_distributed_task(
                    task_id, description, required_skills, priority, context
                )
            elif self.mode == HarnessMode.MULTI_AGENT and EXTENSIONS_AVAILABLE:
                result = self._run_multi_agent_task(
                    task_id, description, required_skills, priority, context
                )
            else:
                result = self._run_local_task(
                    task_id, description, required_skills, context, messages
                )

            # 3. 记录结果
            duration = time.time() - start_time
            task_result = TaskResult(
                task_id=task_id,
                status=result.get("status", "completed"),
                result=result.get("output", ""),
                agent_id=result.get("agent_id"),
                duration=duration,
                artifacts=result.get("artifacts", {}),
                errors=result.get("errors", [])
            )

            self.task_history.append(task_result)

            # 4. 保存到知识库
            if use_rag and EXTENSIONS_AVAILABLE:
                self.rag.add_memory(
                    f"Task: {description}, Result: {result.get('status')}",
                    memory_type="task_record",
                    importance=0.6
                )

            print(f"[IntegratedHarness] Task completed in {duration:.2f}s")
            return task_result

        except Exception as e:
            duration = time.time() - start_time
            error_result = TaskResult(
                task_id=task_id,
                status="failed",
                result=None,
                agent_id=None,
                duration=duration,
                errors=[str(e)]
            )
            self.task_history.append(error_result)
            print(f"[IntegratedHarness] Task failed: {e}")
            return error_result

    def _run_local_task(
        self,
        task_id: str,
        description: str,
        required_skills: List[str],
        context: Dict,
        messages: List[Dict]
    ) -> Dict:
        """本地单Agent任务"""
        # 简单实现：使用shell命令模拟
        output = f"Processed: {description}"
        
        # 如果有RAG上下文，显示检索到的知识
        if messages:
            print(f"  Using {len(messages)} context messages from RAG")

        return {
            "status": "completed",
            "output": output,
            "agent_id": "local",
            "artifacts": {}
        }

    def _run_multi_agent_task(
        self,
        task_id: str,
        description: str,
        required_skills: List[str],
        priority: int,
        context: Dict
    ) -> Dict:
        """多Agent协作任务"""
        # 添加任务到队列
        task = self.multi_agent.add_task(
            description=description,
            required_skills=required_skills,
            priority=priority
        )

        # 触发任务分配
        result = self.multi_agent.distributor.assign_next()
        
        if result:
            assigned_task, agent_id = result
            return {
                "status": "completed",
                "output": f"Assigned to {agent_id}: {description}",
                "agent_id": agent_id,
                "artifacts": {"task_id": task}
            }
        
        return {
            "status": "completed",
            "output": f"No agent available, queued: {description}",
            "agent_id": None,
            "artifacts": {}
        }

    def _run_distributed_task(
        self,
        task_id: str,
        description: str,
        required_skills: List[str],
        priority: int,
        context: Dict
    ) -> Dict:
        """分布式任务"""
        if not self.distributed:
            # 初始化分布式协调器
            self.distributed = DistributedCoordinator(
                self.project_root,
                f"node_{uuid.uuid4().hex[:6]}"
            )

        # 注册并分配任务
        dist_task_id = self.distributed.register_task(
            description=description,
            capabilities=required_skills,
            priority=priority
        )

        self.distributed.assign_task(dist_task_id)

        return {
            "status": "completed",
            "output": f"Distributed task registered: {dist_task_id}",
            "agent_id": "distributed",
            "artifacts": {"dist_task_id": dist_task_id}
        }

    def _run_workflow_task(
        self,
        task_id: str,
        description: str,
        required_skills: List[str],
        template_name: str,
        context: Dict
    ) -> Dict:
        """工作流任务"""
        workflow_context = context or {}
        workflow_context["task"] = description

        result = self.workflow_engine.run_workflow(
            template_name,
            context=workflow_context,
            metadata={"task_id": task_id}
        )

        return {
            "status": result.status.value,
            "output": f"Workflow {result.status.value}: {result.instance_id}",
            "agent_id": "workflow",
            "artifacts": result.artifacts
        }

    # ============ Workflow Integration ============

    def create_custom_workflow(
        self,
        name: str,
        stages: List[Dict]
    ) -> str:
        """创建自定义工作流"""
        from workflow_engine import Stage, StageStatus, GateType, WorkflowTemplate

        stage_objects = []
        for s in stages:
            stage = Stage(
                name=s["name"],
                description=s.get("description", ""),
                agent_role=s.get("agent_role", "agent"),
                required_skills=s.get("required_skills", []),
                gate_type=GateType(s.get("gate_type", "automatic")),
                max_retries=s.get("max_retries", 2),
                timeout=s.get("timeout", 300.0)
            )
            stage_objects.append(stage)

        template = WorkflowTemplate(
            name=name,
            description=f"Custom workflow: {name}",
            stages=stage_objects
        )

        self.workflow_engine.register_template(template)
        return name

    def run_workflow(
        self,
        template_name: str,
        initial_context: Dict = None
    ) -> Dict:
        """运行预定义工作流"""
        if not EXTENSIONS_AVAILABLE:
            return {"status": "failed", "error": "Extensions not available"}

        result = self.workflow_engine.run_workflow(
            template_name,
            context=initial_context
        )

        return {
            "status": result.status.value,
            "instance_id": result.instance_id,
            "stages": result.stage_results,
            "artifacts": result.artifacts
        }

    # ============ Permission & Security ============

    def check_permission(
        self,
        agent_id: str,
        operation: str,
        target: str
    ) -> bool:
        """检查权限"""
        if not EXTENSIONS_AVAILABLE:
            return True

        op_map = {
            "read": OperationType.FILE_READ,
            "write": OperationType.FILE_WRITE,
            "delete": OperationType.FILE_DELETE,
            "execute": OperationType.COMMAND_EXECUTE,
            "network": OperationType.NETWORK_ACCESS
        }

        op = op_map.get(operation)
        if op:
            return self.sandbox.check_file_access(target, op, agent_id)
        
        return True

    def execute_command(
        self,
        command: str,
        agent_id: str = "default"
    ) -> str:
        """执行命令（带权限控制）"""
        if not EXTENSIONS_AVAILABLE:
            return "[Extensions not available]"

        return self.cmd_executor.execute(command, agent_id)

    def get_audit_log(self, limit: int = 50) -> List[Dict]:
        """获取审计日志"""
        if not EXTENSIONS_AVAILABLE:
            return []

        logs = self.sandbox.get_audit_logs(limit)
        return [
            {
                "operation": log.operation.value,
                "target": log.target,
                "agent_id": log.agent_id,
                "result": log.result,
                "timestamp": log.timestamp
            }
            for log in logs
        ]

    # ============ Knowledge & Context ============

    def query_knowledge(self, query: str) -> List[str]:
        """查询知识库"""
        if not EXTENSIONS_AVAILABLE:
            return []

        return self.rag.search_knowledge(query)

    def add_knowledge(
        self,
        content: str,
        content_type: str = "document"
    ):
        """添加知识"""
        if not EXTENSIONS_AVAILABLE:
            return

        from rag_enhanced_context import ChunkType

        self.rag.vector_store.add_chunk(
            type('Chunk', (), {
                'chunk_id': f"manual_{uuid.uuid4().hex[:8]}",
                'content': content,
                'chunk_type': ChunkType[content_type.upper()],
                'source_file': 'manual',
                'importance': 0.8
            })()
        )

    # ============ Status & Monitoring ============

    def get_status(self) -> Dict:
        """获取Harness状态"""
        status = {
            "mode": self.mode.value,
            "agents": list(self.agent_configs.keys()),
            "tasks_completed": len(self.task_history),
            "extensions_available": EXTENSIONS_AVAILABLE
        }

        if EXTENSIONS_AVAILABLE:
            status["multi_agent"] = self.multi_agent.get_status()
            status["workflows"] = self.workflow_engine.get_history(limit=5)
            status["sandbox"] = self.sandbox.generate_report()
            status["rag_chunks"] = len(self.rag.vector_store.chunks)

        return status

    def get_task_history(self, limit: int = 10) -> List[Dict]:
        """获取任务历史"""
        return [
            {
                "task_id": t.task_id,
                "status": t.status,
                "agent_id": t.agent_id,
                "duration": t.duration,
                "errors": t.errors
            }
            for t in self.task_history[-limit:]
        ]


# ============ Convenience Functions ============

def create_harness(
    project_root: Path = None,
    mode: HarnessMode = HarnessMode.LOCAL
) -> IntegratedHarness:
    """创建集成Harness"""
    if project_root is None:
        project_root = Path.cwd()
    
    return IntegratedHarness(project_root, mode)


def create_full_featured_harness(project_root: Path = None) -> IntegratedHarness:
    """创建完整功能的Harness（多Agent + RAG + Workflow）"""
    harness = create_harness(project_root, HarnessMode.MULTI_AGENT)

    # 注册多个专业Agent
    harness.register_agent("coder", ["python", "javascript"], ["backend"], "read_write")
    harness.register_agent("reviewer", ["code_review", "security"], ["security"], "read_only")
    harness.register_agent("tester", ["testing", "debugging"], ["qa"], "read_write")
    harness.register_agent("deployer", ["devops", "cloud"], ["infrastructure"], "execute")

    return harness


def demo():
    """演示集成Harness"""
    project_root = Path.cwd()

    print("=== Integrated Harness Demo ===\n")

    # 创建Harness
    harness = create_full_featured_harness(project_root)

    # 显示状态
    print("1. Harness Status:")
    status = harness.get_status()
    print(f"   Mode: {status['mode']}")
    print(f"   Agents: {', '.join(status['agents'])}")
    print(f"   Extensions: {'Available' if status['extensions_available'] else 'Limited'}")

    # 运行本地任务
    print("\n2. Running local task:")
    result = harness.run_task(
        "Build user authentication system",
        required_skills=["python", "security"],
        use_rag=True
    )
    print(f"   Status: {result.status}")
    print(f"   Duration: {result.duration:.2f}s")

    # 查询知识
    print("\n3. Querying knowledge:")
    knowledge = harness.query_knowledge("authentication")
    print(f"   Found {len(knowledge)} relevant documents")

    # 运行工作流
    print("\n4. Running code_review workflow:")
    wf_result = harness.run_workflow(
        "code_review",
        {"task": "Add JWT authentication"}
    )
    print(f"   Status: {wf_result['status']}")

    # 权限测试
    print("\n5. Permission check:")
    has_permission = harness.check_permission("coder", "write", "src/main.py")
    print(f"   coder can write src/main.py: {has_permission}")

    # 审计日志
    print("\n6. Audit log:")
    logs = harness.get_audit_log(limit=3)
    for log in logs:
        print(f"   - {log['operation']}: {log['target']} -> {log['result']}")

    # 任务历史
    print("\n7. Task history:")
    history = harness.get_task_history()
    for h in history:
        print(f"   - {h['task_id']}: {h['status']} ({h['duration']:.2f}s)")

    print("\n[Demo completed]")


if __name__ == "__main__":
    demo()
