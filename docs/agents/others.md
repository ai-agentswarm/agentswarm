# Other Agents

Agentswarm includes several specialized agents designed for functional composition. These agents are typically used as tools within a `ReActAgent` loop or composed together in a pipeline.

## MapReduce Agent

The `MapReduceAgent` is a powerful tool for scaling operations. It takes a list of items and an "instructed agent". It applies the instruction to every item in the list in parallel (Map) and then synthesizes the results (Reduce).

**Use Case**: Summarizing 10 different news articles at once.

::: agentswarm.agents.MapReduceAgent

## Gathering Agent

The `GatheringAgent` is designed to extract information present in the Context. Unlike other agents that might search externally or generate new content, this agent focuses on reading the message history and extracting specific structured data.

**Use Case**: Extracting a user's name and email from a long conversation history.

::: agentswarm.agents.GatheringAgent

## Merge Agent

The `MergeAgent` is a simple utility to combine multiple text inputs or results into a single coherent response.

**Use Case**: Combining the results of three different search queries into a single paragraph.

::: agentswarm.agents.MergeAgent

## Transformer Agent

The `TransformerAgent` transforms data from one format to another (e.g., JSON to CSV, or text to structured data) based on natural language instructions.

**Use Case**: Converting a messy text list into a clean JSON array.

::: agentswarm.agents.TransformerAgent

## Thinking Agent

The `ThinkingAgent` is unique. It is not usually meant to be called by the user directly. Instead, it is injected into the `ReActAgent` loop to allow the LLM to "think out loud" before taking actions.

It enables the **Chain of Thought** prompting technique within the agent execution flow.

::: agentswarm.agents.ThinkingAgent
