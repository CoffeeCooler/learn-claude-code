#!/usr/bin/env python3
# Harness Extension: Multi-Agent Collaboration with Advanced Communication Protocols
"""
s09_extended_multi_agent.py - Extended Multi-Agent Collaboration

基于s09_agent_teams.py扩展的多Agent协作Harness，包含：
1. 丰富的消息类型（任务、心跳、状态同步、结果共享）
2. 动态任务分配策略
3. Agent能力描述与自动匹配
4. 冲突检测与解决机制
5. 优先级队列管理

    +------------------+     +------------------+
    |   Task Queue    |     |  Agent Registry  |
    |  (Priority Q)   |     | (Capability Map)  |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +--------+---------+     +--------+---------+
    |  Task Distributor |     | Agent Pool       |
    |  (Strategy: Best  |     | - coder          |
    |   Match/Split/   |     | - reviewer       |
    |   RoundRobin)    |     | - tester         |
    +--------+---------+     +--------+---------+
             |                        |
             +----------+-------------+
                        |
                        v
            +---------------------+
            |  Message Bus        |
            |  (JSONL + Pub/Sub) |
            +--------+----------+
                     |
        +------------+------+------------+
        |            |            |         |
        v            v            v         v
   +-------+    +-------+   +-------+ +-------+
   |Agent A|    |Agent B|   |Agent C| |...   |
   +-------+    +-------+   +-------+ +-------+

扩展方向：
- 基于JSONL邮箱扩展为更丰富的消息类型
- 实现动态任务分配策略
- 添加冲突解决机制
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
from queue import PriorityQueue
from typing import Any, Callable, Dict, List, Optional

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv(override=True)

if os.getenv("ANTHROPIC_BASE_URL"):
    os.environ.pop("ANTHROPIC_AUTH_TOKEN", None)

WORKDIR = Path.cwd()
MAILBOX_DIR = WORKDIR / ".agent_mailboxes"
MODEL = os.environ["MODEL_ID"]


class TaskStatus(Enum):
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class MessageType(Enum):
    TASK = "task"
    TASK_RESULT = "task_result"
    HEARTBEAT = "heartbeat"
    STATUS_SYNC = "status_sync"
    CAPABILITY_ADVERTISE = "capability_advertise"
    CONFLICT_DETECT = "conflict_detect"
    CONFLICT_RESOLVE = "conflict_resolve"
    SHUTDOWN = "shutdown"
    CANCEL = "cancel"


class DistributionStrategy(Enum):
    BEST_MATCH = "best_match"  # 最优匹配
    SPLIT = "split"  # 任务拆分
    ROUND_ROBIN = "round_robin"  # 轮询
    LOAD_BALANCE = "load_balance"  # 负载均衡


@dataclass
class AgentCapability:
    name: str
    skills: List[str]
    max_concurrent: int = 2
    specialty: List[str] = field(default_factory=list)


@dataclass
class Task:
    id: str
    description: str
    required_skills: List[str]
    priority: int = 5  # 1-10, 10 highest
    status: TaskStatus = TaskStatus.PENDING
    assigned_to: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class AgentMessage:
    id: str
    msg_type: MessageType
    sender: str
    recipient: Optional[str]  # None = broadcast
    task_id: Optional[str]
    content: Any
    timestamp: float = field(default_factory=time.time)


class ConflictDetector:
    """冲突检测器 - 检测任务执行中的资源冲突"""

    def __init__(self):
        self.locked_resources: Dict[str, List[str]] = defaultdict(list)  # resource -> [task_ids]
        self.pending_conflicts: List[Dict] = []

    def lock(self, task_id: str, resources: List[str]) -> bool:
        """尝试锁定资源"""
        for resource in resources:
            if resource in self.locked_resources:
                self.pending_conflicts.append({
                    "type": "resource_conflict",
                    "task_id": task_id,
                    "holder": self.locked_resources[resource],
                    "resource": resource
                })
                return False
        for resource in resources:
            self.locked_resources[resource].append(task_id)
        return True

    def unlock(self, task_id: str, resources: List[str]):
        """释放资源"""
        for resource in resources:
            if task_id in self.locked_resources[resource]:
                self.locked_resources[resource].remove(task_id)

    def detect_file_conflict(self, task_id: str, file_paths: List[str]) -> bool:
        """检测文件冲突"""
        return not self.lock(task_id, file_paths)


class PriorityTaskQueue:
    """优先级任务队列"""

    def __init__(self):
        self.queue: PriorityQueue = PriorityQueue()
        self.task_map: Dict[str, Task] = {}
        self.id_counter = 0

    def add(self, task: Task) -> str:
        task.id = f"task_{self.id_counter}_{int(time.time() * 1000)}"
        self.id_counter += 1
        self.task_map[task.id] = task
        # priority取负数实现最大堆
        self.queue.put((-task.priority, task.id))
        return task.id

    def get_next(self) -> Optional[Task]:
        if self.queue.empty():
            return None
        _, task_id = self.queue.get()
        return self.task_map.get(task_id)

    def update_status(self, task_id: str, status: TaskStatus):
        if task_id in self.task_map:
            self.task_map[task_id].status = status
            self.task_map[task_id].updated_at = time.time()

    def get_pending(self) -> List[Task]:
        return [t for t in self.task_map.values() if t.status == TaskStatus.PENDING]


class AgentRegistry:
    """Agent注册表 - 管理Agent能力和状态"""

    def __init__(self):
        self.agents: Dict[str, AgentCapability] = {}
        self.agent_status: Dict[str, str] = {}  # agent_id -> status
        self.agent_load: Dict[str, int] = defaultdict(int)  # agent_id -> current_task_count
        self.heartbeats: Dict[str, float] = {}  # agent_id -> last_heartbeat

    def register(self, agent_id: str, capability: AgentCapability):
        self.agents[agent_id] = capability
        self.agent_status[agent_id] = "idle"
        self.heartbeats[agent_id] = time.time()

    def update_heartbeat(self, agent_id: str):
        self.heartbeats[agent_id] = time.time()

    def is_alive(self, agent_id: str, timeout: float = 30.0) -> bool:
        if agent_id not in self.heartbeats:
            return False
        return (time.time() - self.heartbeats[agent_id]) < timeout

    def get_best_agent(self, required_skills: List[str]) -> Optional[str]:
        """获取最佳匹配的Agent"""
        best_agent = None
        best_score = -1

        for agent_id, cap in self.agents.items():
            if not self.is_alive(agent_id):
                continue
            if self.agent_load[agent_id] >= cap.max_concurrent:
                continue

            score = sum(1 for skill in required_skills if skill in cap.skills)
            if score > best_score:
                best_score = score
                best_agent = agent_id

        return best_agent if best_score > 0 else None

    def get_available_agents(self) -> List[str]:
        """获取当前可用的Agent列表"""
        available = []
        for agent_id in self.agents:
            if self.is_alive(agent_id) and self.agent_load[agent_id] < self.agents[agent_id].max_concurrent:
                available.append(agent_id)
        return available


class MessageBus:
    """消息总线 - 支持发布/订阅和点对点消息"""

    def __init__(self, mailbox_dir: Path):
        self.mailbox_dir = mailbox_dir
        self.mailbox_dir.mkdir(exist_ok=True)
        self.subscribers: Dict[str, List[Callable]] = defaultdict(list)
        self.lock = threading.Lock()

    def publish(self, message: AgentMessage):
        """发布消息"""
        with self.lock:
            for callback in self.subscribers.get(message.msg_type.value, []):
                callback(message)
            for callback in self.subscribers.get("*", []):
                callback(message)

    def subscribe(self, msg_type: str, callback: Callable):
        """订阅消息"""
        self.subscribers[msg_type].append(callback)

    def send_to(self, message: AgentMessage):
        """发送消息到指定Agent"""
        mailbox = self.mailbox_dir / f"{message.recipient}.jsonl"
        with open(mailbox, "a") as f:
            f.write(json.dumps({
                "id": message.id,
                "type": message.msg_type.value,
                "sender": message.sender,
                "task_id": message.task_id,
                "content": message.content,
                "timestamp": message.timestamp
            }) + "\n")
        self.publish(message)

    def broadcast(self, message: AgentMessage):
        """广播消息"""
        for agent_id in self._list_agents():
            message.recipient = agent_id
            self.send_to(message)

    def receive(self, agent_id: str) -> List[AgentMessage]:
        """接收消息"""
        messages = []
        mailbox = self.mailbox_dir / f"{agent_id}.jsonl"
        if not mailbox.exists():
            return messages
        with open(mailbox, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    messages.append(AgentMessage(
                        id=data["id"],
                        msg_type=MessageType(data["type"]),
                        sender=data["sender"],
                        recipient=agent_id,
                        task_id=data.get("task_id"),
                        content=data["content"],
                        timestamp=data["timestamp"]
                    ))
                except:
                    pass
        return messages

    def clear(self, agent_id: str):
        """清空Agent邮箱"""
        mailbox = self.mailbox_dir / f"{agent_id}.jsonl"
        if mailbox.exists():
            mailbox.unlink()

    def _list_agents(self) -> List[str]:
        agents = []
        for f in self.mailbox_dir.glob("*.jsonl"):
            agents.append(f.stem)
        return agents


class TaskDistributor:
    """任务分配器 - 多种分配策略"""

    def __init__(
        self,
        registry: AgentRegistry,
        queue: PriorityTaskQueue,
        strategy: DistributionStrategy = DistributionStrategy.BEST_MATCH
    ):
        self.registry = registry
        self.queue = queue
        self.strategy = strategy

    def assign_next(self) -> Optional[tuple]:
        """分配下一个任务"""
        task = self.queue.get_next()
        if not task:
            return None

        if self.strategy == DistributionStrategy.BEST_MATCH:
            agent_id = self.registry.get_best_agent(task.required_skills)
        elif self.strategy == DistributionStrategy.ROUND_ROBIN:
            available = self.registry.get_available_agents()
            agent_id = available[0] if available else None
        elif self.strategy == DistributionStrategy.LOAD_BALANCE:
            agent_id = min(
                self.registry.get_available_agents(),
                key=lambda a: self.registry.agent_load[a]
            ) if self.registry.get_available_agents() else None
        else:
            agent_id = None

        if agent_id:
            task.status = TaskStatus.ASSIGNED
            task.assigned_to = agent_id
            self.registry.agent_load[agent_id] += 1
            return task, agent_id
        else:
            self.queue.queue.put((-task.priority, task.id))
            return None


class MultiAgentHarness:
    """多Agent协作Harness主类"""

    def __init__(
        self,
        workdir: Path,
        strategy: DistributionStrategy = DistributionStrategy.BEST_MATCH
    ):
        self.workdir = workdir
        self.mailbox_dir = workdir / ".agent_mailboxes"
        
        self.registry = AgentRegistry()
        self.task_queue = PriorityTaskQueue()
        self.message_bus = MessageBus(self.mailbox_dir)
        self.conflict_detector = ConflictDetector()
        self.distributor = TaskDistributor(
            self.registry,
            self.task_queue,
            strategy
        )
        
        self.running = False
        self.agent_threads: Dict[str, threading.Thread] = {}

    def register_agent(self, agent_id: str, skills: List[str], specialty: List[str] = None):
        """注册Agent"""
        capability = AgentCapability(
            name=agent_id,
            skills=skills,
            specialty=specialty or []
        )
        self.registry.register(agent_id, capability)

    def add_task(self, description: str, required_skills: List[str], priority: int = 5, dependencies: List[str] = None) -> str:
        """添加任务"""
        task = Task(
            id="",
            description=description,
            required_skills=required_skills,
            priority=priority,
            dependencies=dependencies or []
        )
        return self.task_queue.add(task)

    def start(self):
        """启动Harness"""
        self.running = True
        print("[MultiAgentHarness] Started")
        
        # 启动任务分配循环
        while self.running:
            result = self.distributor.assign_next()
            if result:
                task, agent_id = result
                msg = AgentMessage(
                    id=str(uuid.uuid4()),
                    msg_type=MessageType.TASK,
                    sender="harness",
                    recipient=agent_id,
                    task_id=task.id,
                    content={
                        "description": task.description,
                        "priority": task.priority
                    }
                )
                self.message_bus.send_to(msg)
            time.sleep(0.5)

    def stop(self):
        """停止Harness"""
        self.running = False
        print("[MultiAgentHarness] Stopped")

    def get_status(self) -> Dict:
        """获取状态"""
        return {
            "agents": {
                aid: {
                    "status": self.registry.agent_status.get(aid, "unknown"),
                    "load": self.registry.agent_load.get(aid, 0),
                    "alive": self.registry.is_alive(aid)
                }
                for aid in self.registry.agents
            },
            "tasks": {
                "pending": len(self.task_queue.get_pending()),
                "total": len(self.task_queue.task_map)
            },
            "conflicts": len(self.conflict_detector.pending_conflicts)
        }


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=WORKDIR,
                         capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def demo():
    """演示多Agent协作"""
    harness = MultiAgentHarness(
        WORKDIR,
        DistributionStrategy.BEST_MATCH
    )

    # 注册不同能力的Agent
    harness.register_agent("coder", ["python", "javascript", "typescript"], ["backend", "frontend"])
    harness.register_agent("reviewer", ["code_review", "security"], ["security", "quality"])
    harness.register_agent("tester", ["testing", "debugging"], ["qa"])

    # 添加任务
    harness.add_task("Implement user authentication", ["python", "security"], priority=8)
    harness.add_task("Write unit tests", ["testing", "python"], priority=6)
    harness.add_task("Review security implementation", ["security", "code_review"], priority=7)

    # 显示状态
    print("\n=== Initial Status ===")
    status = harness.get_status()
    print(json.dumps(status, indent=2))

    print("\n=== Task Queue ===")
    for task in harness.task_queue.get_pending():
        print(f"  - {task.description} (priority: {task.priority})")

    print("\n=== Agent Capabilities ===")
    for agent_id, cap in harness.registry.agents.items():
        print(f"  {agent_id}: {cap.skills}")

    # 模拟任务分配
    print("\n=== Task Distribution ===")
    for _ in range(3):
        result = harness.distributor.assign_next()
        if result:
            task, agent_id = result
            print(f"  Assigned '{task.description}' -> {agent_id}")

    print("\n[Demo completed]")


if __name__ == "__main__":
    demo()
