#!/usr/bin/env python3
# Harness Extension: RAG-Enhanced Context Compression
"""
rag_enhanced_context.py - RAG增强上下文压缩

基于s06_context_compact.py和s05_skill_loading.py扩展：
1. 外部知识库集成
2. 向量检索增强
3. 智能上下文重建
4. 相关文档自动注入
5. 长期记忆存储

    +------------------+     +------------------+
    |   Knowledge     |     |   Vector Store   |
    |   Repository    |     |   (Embeddings)   |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +--------+---------+     +--------+---------+
    | Document      |     |  Similarity       |
    | Indexer       |     |  Search          |
    +--------+---------+     +--------+---------+
             |                        |
             v                        v
    +----------------------------------------+
    |      Context Reconstruction Engine      |
    |  - Relevant chunks retrieval          |
    |  - Historical summary integration      |
    |  - Skill injection                    |
    +----------------------------------------+
             |
             v
    +--------+---------+
    | Agent Context    |
    +-----------------+

扩展方向：
- 在压缩策略中增加向量检索步骤
- 实现相关文档的自动注入
- 添加代码库语义理解
"""

import hashlib
import json
import os
import re
import subprocess
import time
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
import math


class ChunkType(Enum):
    CODE = "code"
    DOCUMENT = "document"
    CONVERSATION = "conversation"
    SKILL = "skill"
    TASK = "task"


@dataclass
class DocumentChunk:
    """文档块"""
    chunk_id: str
    content: str
    chunk_type: ChunkType
    source_file: Optional[str]
    embedding: List[float] = field(default_factory=list)
    importance: float = 0.5
    last_accessed: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class MemoryEntry:
    """记忆条目"""
    memory_id: str
    content: str
    embedding: List[float]
    memory_type: str  # "fact", "pattern", "decision", "context"
    importance: float
    created_at: float = field(default_factory=time.time)
    last_retrieved: Optional[float] = None
    retrieval_count: int = 0


class SimpleVectorStore:
    """简化向量存储（无需外部依赖）"""

    def __init__(self, store_dir: Path):
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)
        self.chunks: Dict[str, DocumentChunk] = {}
        self.memories: Dict[str, MemoryEntry] = {}

    def _compute_embedding(self, text: str) -> List[float]:
        """简单的文本嵌入（基于词频）"""
        words = re.findall(r'\w+', text.lower())
        word_freq = defaultdict(int)
        for word in words:
            word_freq[word] += 1

        # 使用hash作为伪随机种子生成固定维度的向量
        embedding = []
        for i in range(128):  # 128维向量
            seed = hashlib.md5(f"{i}_{text}".encode()).digest()
            value = sum(seed) / 256.0
            # 加入词频影响
            for word, freq in word_freq.items():
                if word in text[i:i+10]:
                    value += freq * 0.1
            embedding.append(value)

        # 归一化
        norm = math.sqrt(sum(x**2 for x in embedding))
        if norm > 0:
            embedding = [x/norm for x in embedding]
        return embedding

    def add_chunk(self, chunk: DocumentChunk):
        """添加文档块"""
        chunk.embedding = self._compute_embedding(chunk.content)
        self.chunks[chunk.chunk_id] = chunk
        self._save_chunk(chunk)

    def add_memory(self, memory: MemoryEntry):
        """添加记忆"""
        memory.embedding = self._compute_embedding(memory.content)
        self.memories[memory.memory_id] = memory

    def search_similar(self, query: str, top_k: int = 5, chunk_types: List[ChunkType] = None) -> List[Tuple[DocumentChunk, float]]:
        """相似性搜索"""
        query_embedding = self._compute_embedding(query)
        results = []

        for chunk in self.chunks.values():
            if chunk_types and chunk.chunk_type not in chunk_types:
                continue

            # 计算余弦相似度
            similarity = sum(
                q * c for q, c in zip(query_embedding, chunk.embedding)
            )
            results.append((chunk, similarity))

        # 更新访问信息
        for chunk, _ in results[:top_k]:
            chunk.access_count += 1
            chunk.last_accessed = time.time()

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def search_memories(self, query: str, memory_type: str = None, top_k: int = 3) -> List[Tuple[MemoryEntry, float]]:
        """搜索记忆"""
        query_embedding = self._compute_embedding(query)
        results = []

        for memory in self.memories.values():
            if memory_type and memory.memory_type != memory_type:
                continue

            similarity = sum(
                q * c for q, c in zip(query_embedding, memory.embedding)
            )
            results.append((memory, similarity))

        # 更新检索信息
        for memory, _ in results[:top_k]:
            memory.retrieval_count += 1
            memory.last_retrieved = time.time()

        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]

    def _save_chunk(self, chunk: DocumentChunk):
        """保存块到磁盘"""
        chunk_file = self.store_dir / f"{chunk.chunk_id}.json"
        with open(chunk_file, "w") as f:
            json.dump({
                "chunk_id": chunk.chunk_id,
                "content": chunk.content,
                "chunk_type": chunk.chunk_type.value,
                "source_file": chunk.source_file,
                "importance": chunk.importance,
                "access_count": chunk.access_count,
                "last_accessed": chunk.last_accessed
            }, f)


class KnowledgeIndexer:
    """知识索引器"""

    def __init__(self, vector_store: SimpleVectorStore):
        self.vector_store = vector_store

    def index_directory(self, directory: Path, extensions: List[str] = None):
        """索引目录"""
        extensions = extensions or [".py", ".js", ".ts", ".md", ".txt", ".json"]

        for ext in extensions:
            for file_path in directory.rglob(f"*{ext}"):
                self._index_file(file_path)

    def _index_file(self, file_path: Path):
        """索引单个文件"""
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            chunks = self._chunk_content(content, file_path.name)

            for i, chunk_content in enumerate(chunks):
                chunk = DocumentChunk(
                    chunk_id=f"{file_path.name}_{i}",
                    content=chunk_content,
                    chunk_type=self._detect_chunk_type(file_path),
                    source_file=str(file_path),
                    importance=self._calculate_importance(chunk_content)
                )
                self.vector_store.add_chunk(chunk)
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")

    def _chunk_content(self, content: str, max_chunk_size: int = 1000) -> List[str]:
        """分块内容"""
        lines = content.split('\n')
        chunks = []
        current_chunk = []

        for line in lines:
            current_chunk.append(line)
            if sum(len(l) for l in current_chunk) > max_chunk_size:
                if current_chunk:
                    chunks.append('\n'.join(current_chunk))
                    current_chunk = []

        if current_chunk:
            chunks.append('\n'.join(current_chunk))

        return chunks

    def _detect_chunk_type(self, file_path: Path) -> ChunkType:
        """检测块类型"""
        ext = file_path.suffix
        if ext in [".py", ".js", ".ts", ".jsx", ".tsx"]:
            return ChunkType.CODE
        elif ext in [".md", ".txt"]:
            return ChunkType.DOCUMENT
        return ChunkType.DOCUMENT

    def _calculate_importance(self, content: str) -> float:
        """计算重要性"""
        importance = 0.5

        # 函数/类定义增加重要性
        if re.search(r'^def |^class ', content, re.MULTILINE):
            importance += 0.2

        # 文档注释增加重要性
        if re.search(r'""".*?"""|\'\'\'.*?\'\'', content, re.DOTALL):
            importance += 0.1

        # TODO/FIXME增加重要性
        if re.search(r'# TODO|# FIXME|# NOTE', content):
            importance += 0.1

        return min(importance, 1.0)


class ContextReconstructor:
    """上下文重建器"""

    def __init__(self, vector_store: SimpleVectorStore):
        self.vector_store = vector_store
        self.max_context_tokens = 50000

    def reconstruct_context(
        self,
        current_task: str,
        conversation_history: List[Dict],
        system_prompt: str = None
    ) -> Tuple[List[Dict], List[str]]:
        """重建上下文"""
        reconstructed_messages = []
        injected_knowledge = []

        # 1. 检索相关知识
        relevant_chunks = self.vector_store.search_similar(
            current_task,
            top_k=10,
            chunk_types=[ChunkType.CODE, ChunkType.DOCUMENT]
        )

        for chunk, similarity in relevant_chunks:
            if similarity > 0.3:
                injected_knowledge.append(
                    f"[Related from {chunk.source_file}]: {chunk.content[:500]}"
                )

        # 2. 检索相关记忆
        relevant_memories = self.vector_store.search_memories(
            current_task,
            memory_type="decision",
            top_k=3
        )

        for memory, _ in relevant_memories:
            injected_knowledge.append(
                f"[Past decision]: {memory.content}"
            )

        # 3. 压缩历史对话
        compressed_history = self._compress_history(conversation_history)

        # 4. 构建消息列表
        if system_prompt:
            knowledge_context = "\n\n".join(injected_knowledge)
            enhanced_system = f"{system_prompt}\n\nRelevant Knowledge:\n{knowledge_context}"
            reconstructed_messages.append({
                "role": "system",
                "content": enhanced_system
            })

        reconstructed_messages.extend(compressed_history)

        return reconstructed_messages, injected_knowledge

    def _compress_history(self, history: List[Dict], max_turns: int = 10) -> List[Dict]:
        """压缩历史"""
        if len(history) <= max_turns:
            return history

        # 保留系统消息
        result = [h for h in history if h.get("role") == "system"]

        # 保留最近的对话
        recent = [h for h in history if h.get("role") != "system"][-max_turns:]

        # 添加压缩摘要
        summary = self._generate_summary(history)
        result.append({
            "role": "system",
            "content": f"[Previous conversation summary]: {summary}"
        })

        result.extend(recent)
        return result

    def _generate_summary(self, history: List[Dict]) -> str:
        """生成摘要"""
        # 简单提取关键信息
        tasks = []
        decisions = []

        for msg in history:
            content = msg.get("content", "")
            if isinstance(content, str):
                if "task" in content.lower():
                    tasks.append(content[:100])
                if "decision" in content.lower():
                    decisions.append(content[:100])

        summary_parts = []
        if tasks:
            summary_parts.append(f"Tasks discussed: {len(tasks)}")
        if decisions:
            summary_parts.append(f"Decisions made: {len(decisions)}")

        return "; ".join(summary_parts) if summary_parts else "Previous conversation preserved in memory"


class RAGContextManager:
    """RAG上下文管理器主类"""

    def __init__(self, workdir: Path):
        self.workdir = workdir

        # 初始化存储
        self.store_dir = workdir / ".rag_context"
        self.vector_store = SimpleVectorStore(self.store_dir / "vectors")
        self.indexer = KnowledgeIndexer(self.vector_store)
        self.reconstructor = ContextReconstructor(self.vector_store)

        self._init_knowledge_base()

    def _init_knowledge_base(self):
        """初始化知识库"""
        # 索引项目代码
        print("[RAG] Indexing project knowledge...")
        self.indexer.index_directory(self.workdir / "agents", [".py"])
        self.indexer.index_directory(self.workdir / "docs", [".md"])
        self.indexer.index_directory(self.workdir / "skills", [".md"])
        print(f"[RAG] Indexed {len(self.vector_store.chunks)} chunks")

    def add_memory(self, content: str, memory_type: str = "fact", importance: float = 0.5):
        """添加记忆"""
        memory = MemoryEntry(
            memory_id=f"mem_{int(time.time() * 1000)}",
            content=content,
            embedding=[],  # 将在add_memory中计算
            memory_type=memory_type,
            importance=importance
        )
        self.vector_store.add_memory(memory)

    def get_context(self, task: str, history: List[Dict], system_prompt: str = None) -> List[Dict]:
        """获取增强上下文"""
        messages, knowledge = self.reconstructor.reconstruct_context(
            task, history, system_prompt
        )

        # 记录任务相关决策
        self.add_memory(f"Task: {task}", memory_type="context", importance=0.6)

        return messages

    def search_knowledge(self, query: str) -> List[str]:
        """搜索知识"""
        results = self.vector_store.search_similar(query, top_k=5)
        return [f"[{r[0].source_file}] {r[0].content[:300]}" for r in results]


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        r = subprocess.run(command, shell=True, cwd=Path.cwd(),
                         capture_output=True, text=True, timeout=120)
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"


def demo():
    """演示RAG增强上下文"""
    workdir = Path.cwd()

    # 创建RAG管理器
    rag = RAGContextManager(workdir)

    print("\n=== RAG Context Manager Demo ===\n")

    # 测试知识检索
    print("1. Search knowledge:")
    results = rag.search_knowledge("agent loop tool use")
    for r in results:
        print(f"   - {r[:100]}...\n")

    # 模拟任务历史
    history = [
        {"role": "user", "content": "Build a web server"},
        {"role": "assistant", "content": "I'll create a Flask app with endpoints..."},
        {"role": "user", "content": "Add authentication"},
        {"role": "assistant", "content": "I'll add JWT auth to the server..."},
    ]

    # 获取增强上下文
    print("2. Get enhanced context:")
    context = rag.get_context(
        "Implement user authentication",
        history,
        system_prompt="You are a coding agent."
    )
    print(f"   Context messages: {len(context)}")
    for msg in context[:3]:
        print(f"   - {msg.get('role')}: {str(msg.get('content', ''))[:80]}...")

    # 添加记忆
    print("\n3. Adding memory:")
    rag.add_memory("Used JWT for auth implementation", memory_type="decision")
    print("   Added: 'Used JWT for auth implementation'")

    # 再次检索
    print("\n4. Search again:")
    results = rag.search_knowledge("authentication")
    for r in results:
        print(f"   - {r[:100]}...\n")

    print("[Demo completed]")


if __name__ == "__main__":
    demo()
