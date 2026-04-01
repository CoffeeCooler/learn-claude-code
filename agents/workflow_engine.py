#!/usr/bin/env python3
# Harness Extension: Agent Workflow Engine
"""
workflow_engine.py - Agent工作流引擎

基于s09_extended_multi_agent.py扩展的工作流编排引擎：
1. 定义工作流模板（code -> review -> test -> deploy）
2. 任务阶段自动流转
3. 门禁/检查点机制
4. 工作流状态追踪
5. 失败自动重试与回滚
6. 与Permission Sandbox集成

    +------------------+     +------------------+
    |  Workflow       |     |  Stage          |
    |  Template       |     |  Definitions    |
    +--------+---------+     +--------+---------+
              |                        |
              v                        v
    +--------+---------+     +--------+---------+
    | Workflow      |     | Gate/Checkpoint   |
    | Executor     |     | Manager          |
    +--------+---------+     +--------+---------+
              |                        |
              v                        v
    +----------------------------------------+
    |      Agent Collaboration Layer          |
    |  (Multi-Agent + Permission + RAG)     |
    +----------------------------------------+
              |
              v
    +--------+---------+
    | Workflow State  |
    | Tracker        |
    +-----------------+

扩展方向：
- 集成CI/CD流水线概念
- 添加人工审批门禁
- 实现工作流可视化
"""

import json
import os
import subprocess
import threading
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
import shutil


class StageStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class WorkflowStatus(Enum):
    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class GateType(Enum):
    AUTOMATIC = "automatic"  # 自动检查
    MANUAL = "manual"  # 人工审批
    AGENT_APPROVAL = "agent_approval"  # Agent审批


@dataclass
class Stage:
    """工作流阶段"""
    name: str
    description: str
    agent_role: str  # 执行此阶段的agent角色
    required_skills: List[str]
    gate_type: GateType = GateType.AUTOMATIC
    gate_condition: Optional[Callable] = None  # 通过条件
    retry_count: int = 0
    max_retries: int = 3
    timeout: float = 300.0  # 秒
    status: StageStatus = StageStatus.PENDING
    result: Any = None
    error: Optional[str] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None


@dataclass
class WorkflowTemplate:
    """工作流模板"""
    name: str
    description: str
    stages: List[Stage]
    rollback_on_failure: bool = True
    parallel_stages: List[str] = field(default_factory=list)  # 可并行执行的阶段


@dataclass
class WorkflowInstance:
    """工作流实例"""
    instance_id: str
    template_name: str
    status: WorkflowStatus
    current_stage: Optional[str] = None
    stage_results: Dict[str, Any] = field(default_factory=dict)
    stage_statuses: Dict[str, StageStatus] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    artifacts: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


class GateManager:
    """门禁管理器"""

    def __init__(self):
        self.manual_approvals: Dict[str, Dict] = {}
        self.auto_checks: Dict[str, Callable] = {}

    def register_auto_check(self, stage_name: str, check_fn: Callable):
        """注册自动检查"""
        self.auto_checks[stage_name] = check_fn

    def check_gate(self, stage: Stage, context: Dict) -> bool:
        """检查门禁"""
        if stage.gate_type == GateType.AUTOMATIC:
            if stage.name in self.auto_checks:
                return self.auto_checks[stage.name](context)
            return True  # 无检查则默认通过

        elif stage.gate_type == GateType.MANUAL:
            approval = self.manual_approvals.get(stage.name)
            return approval.get("approved", False) if approval else False

        elif stage.gate_type == GateType.AGENT_APPROVAL:
            # Agent审批需要特定的approval结果
            prev_result = context.get("stage_result")
            return prev_result and prev_result.get("approved", False)

        return False

    def request_manual_approval(self, stage_name: str, requester: str, reason: str) -> str:
        """请求人工审批"""
        approval_id = f"approval_{uuid.uuid4().hex[:8]}"
        self.manual_approvals[stage_name] = {
            "approval_id": approval_id,
            "requester": requester,
            "reason": reason,
            "approved": False,
            "timestamp": time.time()
        }
        return approval_id

    def approve(self, stage_name: str, approver: str) -> bool:
        """审批通过"""
        if stage_name in self.manual_approvals:
            self.manual_approvals[stage_name]["approved"] = True
            self.manual_approvals[stage_name]["approver"] = approver
            return True
        return False

    def reject(self, stage_name: str, reason: str) -> bool:
        """审批拒绝"""
        if stage_name in self.manual_approvals:
            self.manual_approvals[stage_name]["approved"] = False
            self.manual_approvals[stage_name]["reject_reason"] = reason
            return True
        return False


class WorkflowExecutor:
    """工作流执行器"""

    def __init__(self, template: WorkflowTemplate, workdir: Path):
        self.template = template
        self.workdir = workdir
        self.instance: Optional[WorkflowInstance] = None
        self.gate_manager = GateManager()
        self.running = False
        self.current_thread: Optional[threading.Thread] = None

        # Stage执行器映射
        self.stage_executors: Dict[str, Callable] = {}

    def register_stage_executor(self, stage_name: str, executor_fn: Callable):
        """注册阶段执行器"""
        self.stage_executors[stage_name] = executor_fn

    def create_instance(self, metadata: Dict = None) -> WorkflowInstance:
        """创建工作流实例"""
        instance = WorkflowInstance(
            instance_id=f"wf_{uuid.uuid4().hex[:8]}",
            template_name=self.template.name,
            status=WorkflowStatus.CREATED,
            metadata=metadata or {}
        )

        # 初始化阶段状态
        for stage in self.template.stages:
            instance.stage_statuses[stage.name] = StageStatus.PENDING

        self.instance = instance
        return instance

    def run(self, context: Dict = None) -> WorkflowInstance:
        """运行工作流"""
        if not self.instance:
            raise ValueError("No workflow instance created")

        self.running = True
        self.instance.status = WorkflowStatus.RUNNING
        self.instance.started_at = time.time()
        context = context or {}

        try:
            for stage in self.template.stages:
                if not self.running:
                    break

                # 检查是否跳过
                if self.instance.stage_statuses.get(stage.name) == StageStatus.SKIPPED:
                    continue

                # 执行阶段
                success = self._execute_stage(stage, context)
                if not success:
                    if self.template.rollback_on_failure:
                        self._rollback(stage, context)
                    self.instance.status = WorkflowStatus.FAILED
                    break

            if self.running and all(
                s == StageStatus.PASSED
                for s in self.instance.stage_statuses.values()
            ):
                self.instance.status = WorkflowStatus.COMPLETED

        except Exception as e:
            self.instance.status = WorkflowStatus.FAILED
            self.instance.metadata["error"] = str(e)

        finally:
            self.running = False
            self.instance.completed_at = time.time()

        return self.instance

    def _execute_stage(self, stage: Stage, context: Dict) -> bool:
        """执行单个阶段"""
        self.instance.current_stage = stage.name
        self.instance.stage_statuses[stage.name] = StageStatus.RUNNING
        stage.status = StageStatus.RUNNING
        stage.started_at = time.time()

        # 检查门禁
        if not self.gate_manager.check_gate(stage, context):
            self.instance.stage_statuses[stage.name] = StageStatus.BLOCKED
            stage.status = StageStatus.BLOCKED
            return False

        # 执行重试循环
        for attempt in range(stage.max_retries + 1):
            try:
                # 调用执行器
                if stage.name in self.stage_executors:
                    result = self._execute_with_timeout(
                        stage, self.stage_executors[stage.name], context
                    )
                else:
                    result = {"status": "completed", "message": "No executor registered"}

                # 检查结果
                if stage.gate_condition and not stage.gate_condition(result):
                    stage.status = StageStatus.FAILED
                    stage.error = "Gate condition not met"
                    self.instance.stage_statuses[stage.name] = StageStatus.FAILED
                    return False

                # 成功
                stage.result = result
                stage.status = StageStatus.PASSED
                self.instance.stage_statuses[stage.name] = StageStatus.PASSED
                self.instance.stage_results[stage.name] = result

                # 保存artifact
                if "artifact" in result:
                    self.instance.artifacts[stage.name] = result["artifact"]

                return True

            except Exception as e:
                stage.retry_count = attempt + 1
                stage.error = str(e)
                if attempt < stage.max_retries:
                    time.sleep(2 ** attempt)  # 指数退避
                else:
                    stage.status = StageStatus.FAILED
                    self.instance.stage_statuses[stage.name] = StageStatus.FAILED

        return False

    def _execute_with_timeout(self, stage: Stage, executor: Callable, context: Dict) -> Any:
        """带超时的执行"""
        result = [None]
        error = [None]

        def run_stage():
            try:
                result[0] = executor(stage, context, self.instance)
            except Exception as e:
                error[0] = e

        thread = threading.Thread(target=run_stage)
        thread.start()
        thread.join(timeout=stage.timeout)

        if thread.is_alive():
            raise TimeoutError(f"Stage {stage.name} timed out after {stage.timeout}s")

        if error[0]:
            raise error[0]

        return result[0]

    def _rollback(self, failed_stage: Stage, context: Dict):
        """回滚"""
        print(f"[Workflow] Rolling back after {failed_stage.name} failure...")
        # 实现回滚逻辑
        # 可以清理已创建的artifacts，恢复状态等

    def pause(self):
        """暂停工作流"""
        self.running = False
        if self.instance:
            self.instance.status = WorkflowStatus.PAUSED

    def resume(self):
        """恢复工作流"""
        if self.instance and self.instance.status == WorkflowStatus.PAUSED:
            self.running = True
            self.instance.status = WorkflowStatus.RUNNING
            # 从暂停位置继续

    def skip_stage(self, stage_name: str):
        """跳过阶段"""
        if self.instance:
            self.instance.stage_statuses[stage_name] = StageStatus.SKIPPED

    def get_status(self) -> Dict:
        """获取状态"""
        if not self.instance:
            return {}

        return {
            "instance_id": self.instance.instance_id,
            "template": self.template.name,
            "status": self.instance.status.value,
            "current_stage": self.instance.current_stage,
            "stages": {
                name: status.value
                for name, status in self.instance.stage_statuses.items()
            },
            "duration": (
                (self.instance.completed_at or time.time()) - self.instance.started_at
                if self.instance.started_at else 0
            )
        }


# ============ 预定义工作流模板 ============

def create_code_review_workflow() -> WorkflowTemplate:
    """创建代码审查工作流"""
    return WorkflowTemplate(
        name="code_review",
        description="Code -> Review -> Test -> Deploy workflow",
        stages=[
            Stage(
                name="code",
                description="Write code implementation",
                agent_role="coder",
                required_skills=["python", "javascript"],
                gate_type=GateType.AUTOMATIC,
                max_retries=2,
                timeout=600.0
            ),
            Stage(
                name="review",
                description="Code review and feedback",
                agent_role="reviewer",
                required_skills=["code_review", "security"],
                gate_type=GateType.AGENT_APPROVAL,
                max_retries=1,
                timeout=300.0
            ),
            Stage(
                name="test",
                description="Run tests and validation",
                agent_role="tester",
                required_skills=["testing", "debugging"],
                gate_type=GateType.AUTOMATIC,
                gate_condition=lambda r: r.get("tests_passed", False),
                max_retries=2,
                timeout=300.0
            ),
            Stage(
                name="deploy",
                description="Deploy to staging/production",
                agent_role="deployer",
                required_skills=["devops", "cloud"],
                gate_type=GateType.MANUAL,
                max_retries=1,
                timeout=600.0
            )
        ],
        rollback_on_failure=True
    )


def create_bugfix_workflow() -> WorkflowTemplate:
    """创建Bug修复工作流"""
    return WorkflowTemplate(
        name="bugfix",
        description="Reproduce -> Fix -> Test -> Verify workflow",
        stages=[
            Stage(
                name="reproduce",
                description="Reproduce the bug",
                agent_role="investigator",
                required_skills=["debugging", "analysis"],
                gate_type=GateType.AUTOMATIC,
                timeout=180.0
            ),
            Stage(
                name="fix",
                description="Implement the fix",
                agent_role="coder",
                required_skills=["python"],
                gate_type=GateType.AUTOMATIC,
                timeout=300.0
            ),
            Stage(
                name="verify",
                description="Verify the fix works",
                agent_role="tester",
                required_skills=["testing"],
                gate_type=GateType.AUTOMATIC,
                gate_condition=lambda r: r.get("verified", False),
                timeout=180.0
            )
        ],
        rollback_on_failure=False
    )


# ============ 示例执行器 ============

def code_stage_executor(stage: Stage, context: Dict, instance: WorkflowInstance) -> Dict:
    """代码编写阶段执行器"""
    task = context.get("task", "Implement feature")
    print(f"[Stage: {stage.name}] Writing code for: {task}")

    # 模拟代码编写
    time.sleep(1)

    return {
        "status": "completed",
        "files_created": ["feature.py"],
        "artifact": {"code": "def feature(): pass"}
    }


def review_stage_executor(stage: Stage, context: Dict, instance: WorkflowInstance) -> Dict:
    """代码审查阶段执行器"""
    previous_result = instance.stage_results.get("code", {})
    print(f"[Stage: {stage.name}] Reviewing code...")

    # 模拟审查
    time.sleep(0.5)

    # 模拟审查结果
    issues_found = 0  # 假设没有issues
    approved = issues_found == 0

    return {
        "status": "completed",
        "issues_found": issues_found,
        "approved": approved,
        "feedback": "LGTM" if approved else "Please fix issues"
    }


def test_stage_executor(stage: Stage, context: Dict, instance: WorkflowInstance) -> Dict:
    """测试阶段执行器"""
    print(f"[Stage: {stage.name}] Running tests...")

    # 模拟测试
    time.sleep(0.5)

    # 假设测试通过
    return {
        "status": "completed",
        "tests_passed": True,
        "coverage": 85.0,
        "artifact": {"test_results": "all passed"}
    }


def deploy_stage_executor(stage: Stage, context: Dict, instance: WorkflowInstance) -> Dict:
    """部署阶段执行器"""
    print(f"[Stage: {stage.name}] Deploying...")

    # 模拟部署
    time.sleep(0.5)

    return {
        "status": "completed",
        "deployed_to": "staging",
        "artifact": {"deployment_id": "deploy_123"}
    }


class IntegratedWorkflowEngine:
    """集成工作流引擎（整合Multi-Agent + Permission + RAG）"""

    def __init__(self, workdir: Path):
        self.workdir = workdir
        self.templates: Dict[str, WorkflowTemplate] = {}
        self.active_workflows: Dict[str, WorkflowExecutor] = {}
        self.history: List[WorkflowInstance] = []

        # 注册默认模板
        self.register_template(create_code_review_workflow())
        self.register_template(create_bugfix_workflow())

    def register_template(self, template: WorkflowTemplate):
        """注册工作流模板"""
        self.templates[template.name] = template

    def create_workflow(self, template_name: str, metadata: Dict = None) -> WorkflowExecutor:
        """创建工作流"""
        if template_name not in self.templates:
            raise ValueError(f"Template {template_name} not found")

        template = self.templates[template_name]
        executor = WorkflowExecutor(template, self.workdir)

        # 注册默认执行器
        executor.register_stage_executor("code", code_stage_executor)
        executor.register_stage_executor("review", review_stage_executor)
        executor.register_stage_executor("test", test_stage_executor)
        executor.register_stage_executor("deploy", deploy_stage_executor)
        executor.register_stage_executor("fix", code_stage_executor)
        executor.register_stage_executor("verify", test_stage_executor)
        executor.register_stage_executor("reproduce", review_stage_executor)

        instance = executor.create_instance(metadata)
        self.active_workflows[instance.instance_id] = executor

        return executor

    def run_workflow(self, template_name: str, context: Dict = None, metadata: Dict = None) -> WorkflowInstance:
        """运行工作流"""
        executor = self.create_workflow(template_name, metadata)
        instance = executor.run(context)

        # 移到历史
        self.history.append(instance)
        if instance.instance_id in self.active_workflows:
            del self.active_workflows[instance.instance_id]

        return instance

    def get_workflow(self, instance_id: str) -> Optional[WorkflowExecutor]:
        """获取工作流"""
        return self.active_workflows.get(instance_id)

    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取历史"""
        return [
            {
                "instance_id": w.instance_id,
                "template": w.template_name,
                "status": w.status.value,
                "duration": w.completed_at - w.started_at if w.completed_at and w.started_at else 0
            }
            for w in self.history[-limit:]
        ]


def demo():
    """演示工作流引擎"""
    workdir = Path.cwd()

    # 创建引擎
    engine = IntegratedWorkflowEngine(workdir)

    print("=== Workflow Engine Demo ===\n")

    # 列出模板
    print("1. Available templates:")
    for name, template in engine.templates.items():
        print(f"   - {name}: {template.description}")
        for stage in template.stages:
            print(f"       -> {stage.name} ({stage.agent_role})")

    # 运行代码审查工作流
    print("\n2. Running code_review workflow:")
    result = engine.run_workflow(
        "code_review",
        context={"task": "Implement user authentication"},
        metadata={"requester": "demo_user"}
    )

    print(f"\n   Result: {result.status.value}")
    print(f"   Duration: {result.completed_at - result.started_at:.2f}s")
    print("\n   Stage results:")
    for stage_name, stage_result in result.stage_results.items():
        print(f"       - {stage_name}: {stage_result.get('status', 'unknown')}")

    # 显示历史
    print("\n3. Workflow history:")
    history = engine.get_history()
    for h in history:
        print(f"   - {h['template']}: {h['status']}")

    print("\n[Demo completed]")


if __name__ == "__main__":
    demo()
