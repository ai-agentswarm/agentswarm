# 🐝 AgentSwarm

**A Recursive, Functional, and Type-Safe Framework for Autonomous AI Agents.**

**AgentSwarm** is a next-generation agentic orchestration framework designed to solve the critical issues of **Context Pollution** and **Complex Orchestration** in multi-agent systems.

Unlike chat-based frameworks (like AutoGen) or static graph frameworks (like LangGraph), AgentSwarm treats agents as **Strongly Typed Asynchronous Functions** that operate in isolated environments ("Tabula Rasa"), natively supporting recursion and Map-Reduce patterns.

## 🚀 Why AgentSwarm?

Current architectures suffer from two main problems:
1.  **Context Pollution:** Sub-agents inherit the parent's entire chat history, wasting tokens, increasing latency, and confusing the model.
2.  **Boilerplate Hell:** Defining dynamic recursive graphs requires complex configuration and rigid state definitions.

**AgentSwarm solves these problems:**

* **🧠 Tabula Rasa Execution:** Every invoked agent starts with a *clean* context. The sub-agent receives only the specific input required, executes the task, and returns the output. No noise, no context window overflow.
* **📦 Native Blackboard Pattern:** Agents don't pass massive raw text strings back and forth. They use a shared **Key-Value Store** to manipulate, transform, and merge data, exchanging only references (Keys).
* **🛡️ Type-Safe by Design:** Built on Pydantic and Python Generics. Agent inputs and outputs are validated at runtime, and JSON schemas for the LLM are generated automatically from type hints.
* **⚡ Implicit Parallelism:** The `ReActAgent` engine automatically handles parallel tool execution (Map) and result aggregation (Reduce) without complex graph definitions.

## 🛠️ Architecture

AgentSwarm is built on three fundamental concepts:

### 1. Agent-as-a-Function
Every agent is a class inheriting from `BaseAgent[Input, Output]`. There are no "nodes" or "edges" to manually define. Orchestration emerges naturally from the functional calls between agents.
Moreover, agents are **strongly typed** and **asynchronous** by design, making them easy to compose and debug. When errors occur, they are propagated as standard exceptions, that can be managed by agents at different levels.

### 2. The "Store" (Shared Memory)
Instead of overloading the chat context, agents use the `Store` to manage information. We provide a set of agents to ease the management of the store:
* **GatheringAgent:** Retrieves data from the store for display or processing.
* **TransformerAgent:** Transforms data in the store (e.g., summarize, filter) using natural language commands and returns a new Key, keeping the context light.
* **MergeAgent:** Combines multiple data keys into a single entity.

### 3. Recursive Map-Reduce
The Map-Reduce pattern is a powerful way to decompose complex tasks into smaller, parallelizable subtasks. It is used since decades in parallel computing. With AgentSwarm, we borrow this pattern to ease the orchestration of complex tasks, preventing context pullution or exosting, prefering to use the store as a shared memory.
A `MapReduceAgent` can decompose complex tasks, dynamically instantiate clones of itself or other agents, and execute work in parallel, avoiding deadlocks via instance isolation.

### 4. Interoperability & Hybrid Execution
AgentSwarm is designed to be an open ecosystem, not a walled garden.
* **Protocol Agnostic:** It (will) supports the **Model Context Protocol (MCP)** and **Agent-to-Agent (A2A)** standards, allowing your agents to interact seamlessly with external tools and third-party agent networks. You can also easily wrap existing **LangChain** tools and run them within the Swarm.
* **Hybrid Runtime:** Each agent can be executed locally, or remotly, exploiting **AWS** or **Google Cloud** services. Also the Store can be a remote key-value store, like Redis.

