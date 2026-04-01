#!/usr/bin/env python3
# Harness Extension: Distributed Agent Coordinator
"""
distributed_agent_coordinator.py - 分布式Agent协调器

基于s12_worktree_task_isolation.py扩展的分布式协调机制：
1. 跨机器任务协调
2. 基于Redis/ZooKeeper的分布式锁
3. 消息队列集成
4. 故障转移机制
5. 状态同步协议
6. Leader选举

    +------------------+     +------------------+
    |  Coordinator     |     |  Leader Election|
    |  Service        |     |  (Raft/Paxos)  |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +--------+---------+     +--------+---------+
    | Task Registry |     |  Node Registry    |
    | (持久化任务)   |     | (Worker节点)      |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +----------------------------------------+
    |     Distributed Lock Manager            |
    |   (Redis/ZooKeeper/File-based)         |
    +----------------------------------------+
             |
    +--------+---------+     +--------+---------+
    | Message Queue |     |  State Store      |
    | (任务分发)    |     |  (持久化状态)      |
    +--------+---------+     +--------+---------+

扩展方向：
- 将工作树隔离扩展为基于Git或消息队列的分布式协调
- 实现跨机器的Agent通信
- 添加故障检测与自动恢复
"""

import fcntl
import hashlib
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
from typing import Any, Dict, List, Optional, Set
import socket
import struct


class NodeState(Enum):
    UNKNOWN = "unknown"
    STARTING = "starting"
    RUNNING = "running"
    IDLE = "idle"
    BUSY = "busy"
    FAILED = "failed"
    STOPPED = "stopped"


class TaskState(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkerNode:
    """工作节点"""
    node_id: str
    hostname: str
    ip: str
    port: int
    state: NodeState = NodeState.UNKNOWN
    capabilities: List[str] = field(default_factory=list)
    current_tasks: List[str] = field(default_factory=list)
    last_heartbeat: float = field(default_factory=time.time)
    leader: bool = False


@dataclass
class DistributedTask:
    """分布式任务"""
    task_id: str
    description: str
    required_capabilities: List[str]
    priority: int = 5
    state: TaskState = TaskState.PENDING
    assigned_node: Optional[str] = None
    workdir: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    result: Any = None
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    error: Optional[str] = None


class FileBasedLock:
    """基于文件的分布式锁"""

    def __init__(self, lock_dir: Path):
        self.lock_dir = lock_dir
        self.lock_dir.mkdir(parents=True, exist_ok=True)

    def acquire(self, resource: str, timeout: float = 30.0) -> bool:
        """获取锁"""
        lock_file = self.lock_dir / f"{hashlib.md5(resource.encode()).hexdigest()}.lock"
        start_time = time.time()

        while True:
            try:
                fd = os.open(str(lock_file), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                # 写入锁信息
                lock_info = {
                    "resource": resource,
                    "owner": f"{socket.gethostname()}_{os.getpid()}",
                    "timestamp": time.time()
                }
                os.write(fd, json.dumps(lock_info).encode())
                os.close(fd)
                self._current_lock = lock_file
                return True
            except FileExistsError:
                # 检查锁是否过期
                try:
                    with open(lock_file, "r") as f:
                        info = json.loads(f.read())
                        if time.time() - info.get("timestamp", 0) > 300:  # 5分钟超时
                            os.unlink(str(lock_file))
                            continue
                except:
                    pass

                if time.time() - start_time > timeout:
                    return False
                time.sleep(0.1)

    def release(self):
        """释放锁"""
        if hasattr(self, "_current_lock") and self._current_lock.exists():
            self._current_lock.unlink()


class DistributedTaskRegistry:
    """分布式任务注册表"""

    def __init__(self, registry_dir: Path):
        self.registry_dir = registry_dir
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        self.lock_manager = FileBasedLock(registry_dir / ".locks")

    def register_task(self, task: DistributedTask) -> bool:
        """注册任务"""
        if not self.lock_manager.acquire(f"task_{task.task_id}"):
            return False

        try:
            task_file = self.registry_dir / f"{task.task_id}.json"
            with open(task_file, "w") as f:
                json.dump({
                    "task_id": task.task_id,
                    "description": task.description,
                    "required_capabilities": task.required_capabilities,
                    "priority": task.priority,
                    "state": task.state.value,
                    "assigned_node": task.assigned_node,
                    "dependencies": task.dependencies,
                    "created_at": task.created_at
                }, f, indent=2)
            return True
        finally:
            self.lock_manager.release()

    def update_task(self, task_id: str, updates: Dict) -> bool:
        """更新任务"""
        task_file = self.registry_dir / f"{task_id}.json"
        if not task_file.exists():
            return False

        with open(task_file, "r") as f:
            task_data = json.load(f)

        task_data.update(updates)

        with open(task_file, "w") as f:
            json.dump(task_data, f, indent=2)

        return True

    def get_task(self, task_id: str) -> Optional[DistributedTask]:
        """获取任务"""
        task_file = self.registry_dir / f"{task_id}.json"
        if not task_file.exists():
            return None

        with open(task_file, "r") as f:
            data = json.load(f)

        return DistributedTask(
            task_id=data["task_id"],
            description=data["description"],
            required_capabilities=data.get("required_capabilities", []),
            priority=data.get("priority", 5),
            state=TaskState(data.get("state", "pending")),
            assigned_node=data.get("assigned_node"),
            dependencies=data.get("dependencies", []),
            created_at=data.get("created_at", time.time())
        )

    def get_pending_tasks(self) -> List[DistributedTask]:
        """获取待处理任务"""
        tasks = []
        for task_file in self.registry_dir.glob("*.json"):
            try:
                with open(task_file, "r") as f:
                    data = json.load(f)
                if data.get("state") == TaskState.PENDING.value:
                    tasks.append(DistributedTask(
                        task_id=data["task_id"],
                        description=data["description"],
                        required_capabilities=data.get("required_capabilities", []),
                        priority=data.get("priority", 5)
                    ))
            except:
                pass
        return sorted(tasks, key=lambda t: t.priority, reverse=True)

    def get_node_tasks(self, node_id: str) -> List[DistributedTask]:
        """获取节点分配的任务"""
        tasks = []
        for task_file in self.registry_dir.glob("*.json"):
            try:
                with open(task_file, "r") as f:
                    data = json.load(f)
                if data.get("assigned_node") == node_id:
                    tasks.append(DistributedTask(
                        task_id=data["task_id"],
                        description=data["description"],
                        required_capabilities=data.get("required_capabilities", []),
                        state=TaskState(data.get("state", "pending"))
                    ))
            except:
                pass
        return tasks


class NodeRegistry:
    """节点注册表"""

    def __init__(self, registry_dir: Path):
        self.registry_dir = registry_dir
        self.nodes_dir = registry_dir / "nodes"
        self.nodes_dir.mkdir(parents=True, exist_ok=True)

    def register_node(self, node: WorkerNode) -> bool:
        """注册节点"""
        node_file = self.nodes_dir / f"{node.node_id}.json"
        with open(node_file, "w") as f:
            json.dump({
                "node_id": node.node_id,
                "hostname": node.hostname,
                "ip": node.ip,
                "port": node.port,
                "state": node.state.value,
                "capabilities": node.capabilities,
                "leader": node.leader,
                "last_heartbeat": node.last_heartbeat
            }, f, indent=2)
        return True

    def update_heartbeat(self, node_id: str) -> bool:
        """更新心跳"""
        node_file = self.nodes_dir / f"{node_id}.json"
        if not node_file.exists():
            return False

        with open(node_file, "r") as f:
            data = json.load(f)

        data["last_heartbeat"] = time.time()
        data["state"] = NodeState.RUNNING.value

        with open(node_file, "w") as f:
            json.dump(data, f)

        return True

    def get_alive_nodes(self, timeout: float = 30.0) -> List[WorkerNode]:
        """获取存活节点"""
        nodes = []
        for node_file in self.nodes_dir.glob("*.json"):
            try:
                with open(node_file, "r") as f:
                    data = json.load(f)
                if time.time() - data.get("last_heartbeat", 0) < timeout:
                    nodes.append(WorkerNode(
                        node_id=data["node_id"],
                        hostname=data["hostname"],
                        ip=data["ip"],
                        port=data["port"],
                        state=NodeState(data.get("state", "unknown")),
                        capabilities=data.get("capabilities", []),
                        leader=data.get("leader", False)
                    ))
            except:
                pass
        return nodes

    def get_leader(self) -> Optional[WorkerNode]:
        """获取Leader节点"""
        for node_file in self.nodes_dir.glob("*.json"):
            try:
                with open(node_file, "r") as f:
                    data = json.load(f)
                if data.get("leader"):
                    return WorkerNode(
                        node_id=data["node_id"],
                        hostname=data["hostname"],
                        ip=data["ip"],
                        port=data["port"]
                    )
            except:
                pass
        return None


class LeaderElection:
    """Leader选举（简化版）"""

    def __init__(self, registry: NodeRegistry, node_id: str):
        self.registry = registry
        self.node_id = node_id
        self.election_timeout = 5.0

    def request_vote(self) -> bool:
        """请求投票"""
        nodes = self.registry.get_alive_nodes()
        votes = 1  # 自己的一票

        # 简单选举：选择最早启动的节点
        earliest = None
        for node in nodes:
            if node.node_id == self.node_id:
                continue
            if earliest is None or node.last_heartbeat < earliest.last_heartbeat:
                earliest = node

        if earliest and earliest.last_heartbeat < time.time() - self.election_timeout:
            return False

        return True


class DistributedCoordinator:
    """分布式协调器主类"""

    def __init__(self, workdir: Path, node_id: str):
        self.workdir = workdir
        self.node_id = node_id

        # 初始化目录结构
        self.coordinator_dir = workdir / ".coordinator"
        self.task_registry = DistributedTaskRegistry(
            self.coordinator_dir / "tasks"
        )
        self.node_registry = NodeRegistry(
            self.coordinator_dir / "nodes"
        )

        # 注册当前节点
        self.node = WorkerNode(
            node_id=node_id,
            hostname=socket.gethostname(),
            ip=socket.gethostbyname(socket.gethostname()),
            port=8080,
            state=NodeState.RUNNING,
            capabilities=["python", "bash", "file_ops"]
        )
        self.node_registry.register_node(self.node)

        # Leader选举
        self.election = LeaderElection(self.node_registry, node_id)

        self.running = False

    def start_heartbeat(self):
        """启动心跳"""
        def heartbeat():
            while self.running:
                self.node_registry.update_heartbeat(self.node_id)
                time.sleep(5)

        thread = threading.Thread(target=heartbeat, daemon=True)
        thread.start()

    def register_task(self, description: str, capabilities: List[str], priority: int = 5) -> str:
        """注册任务"""
        task = DistributedTask(
            task_id=f"dist_{uuid.uuid4().hex[:8]}",
            description=description,
            required_capabilities=capabilities,
            priority=priority
        )
        self.task_registry.register_task(task)
        return task.task_id

    def assign_task(self, task_id: str) -> bool:
        """分配任务"""
        task = self.task_registry.get_task(task_id)
        if not task:
            return False

        # 查找合适的节点
        nodes = self.node_registry.get_alive_nodes()
        for node in nodes:
            if all(cap in node.capabilities for cap in task.required_capabilities):
                task.assigned_node = node.node_id
                task.state = TaskState.QUEUED
                self.task_registry.update_task(task_id, {
                    "assigned_node": node.node_id,
                    "state": TaskState.QUEUED.value
                })
                return True

        return False

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        task = self.task_registry.get_task(task_id)
        if not task:
            return None
        return {
            "task_id": task.task_id,
            "description": task.description,
            "state": task.state.value,
            "assigned_node": task.assigned_node,
            "result": task.result
        }

    def get_cluster_status(self) -> Dict:
        """获取集群状态"""
        nodes = self.node_registry.get_alive_nodes()
        tasks = self.task_registry.get_pending_tasks()

        return {
            "node_id": self.node_id,
            "is_leader": self.node.leader,
            "cluster_size": len(nodes),
            "alive_nodes": [
                {
                    "node_id": n.node_id,
                    "hostname": n.hostname,
                    "state": n.state.value,
                    "capabilities": n.capabilities
                }
                for n in nodes
            ],
            "pending_tasks": len(tasks)
        }

    def run(self):
        """运行协调器"""
        self.running = True
        self.start_heartbeat()

        # 尝试成为Leader
        if self.election.request_vote():
            self.node.leader = True
            self.node_registry.register_node(self.node)

        print(f"[DistributedCoordinator] Started as {self.node_id}")
        print(f"[DistributedCoordinator] Leader: {self.node.leader}")


def demo():
    """演示分布式协调器"""
    workdir = Path.cwd()

    # 创建协调器（模拟两个节点）
    coord1 = DistributedCoordinator(workdir, "worker-1")
    coord1.run()

    print("\n=== Cluster Status ===")
    status = coord1.get_cluster_status()
    print(json.dumps(status, indent=2))

    # 注册任务
    print("\n=== Registering Tasks ===")
    task1 = coord1.register_task("Build API server", ["python", "backend"], priority=8)
    task2 = coord1.register_task("Write tests", ["python", "testing"], priority=6)
    print(f"Task 1: {task1}")
    print(f"Task 2: {task2}")

    # 分配任务
    print("\n=== Assigning Tasks ===")
    coord1.assign_task(task1)
    coord1.assign_task(task2)

    # 检查状态
    print("\n=== Task Status ===")
    print(json.dumps(coord1.get_task_status(task1), indent=2))
    print(json.dumps(coord1.get_task_status(task2), indent=2))

    coord1.running = False
    print("\n[Demo completed]")


if __name__ == "__main__":
    demo()
