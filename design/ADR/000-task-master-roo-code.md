# ADR 000: Task Master Integration for AI-Driven Development

## Status

Accepted

## Context

The Gwent Companion project is a complex hardware and software system designed to enhance the Gwent card game experience. As the project has grown in complexity, there was a need for a more structured approach to task management, particularly one that could integrate well with AI-driven development workflows.

The original project used a basic task management system defined in `task-list.mdc`, which provided a simple structure for tracking tasks with:
- A 3-digit numbering system (000-999)
- Basic dependency tracking
- Priority levels (High, Medium, Low)
- Status indicators (Not Started, In Progress, Blocked, Completed)
- Task files stored in the design directory

While functional, this system lacked integration with AI tools and had limited capabilities for task breakdown, complexity analysis, and adaptive workflow management. As AI-driven development with tools like Cursor AI became more central to the project's workflow, a more sophisticated task management system was needed.

## Decision

We have decided to integrate the Task Master system, developed by [@eyaltoledano](https://x.com/eyaltoledano), to provide a more robust task management framework that works seamlessly with AI-driven development. The implementation includes:

### 1. CLI Tool and MCP Server

- **CLI Tool**: A Node.js-based command-line interface (`task-master`) that provides comprehensive task management capabilities, including task creation, listing, updating, and status management.
- **MCP Server**: A Model Context Protocol (MCP) server that exposes Task Master functionality through a set of tools, enabling direct integration with AI agents like Cursor AI.

### 2. Task Structure and Management

- **tasks.json**: A central JSON file that serves as the single source of truth for all tasks, replacing the previous task-list.mdc approach.
- **Enhanced Task Structure**: Each task includes:
  - Unique identifier
  - Title and description
  - Status (pending, done, deferred, etc.)
  - Dependencies with status indicators (✅ for completed, ⏱️ for pending)
  - Priority levels
  - Detailed implementation instructions
  - Test strategies
  - Subtasks for breaking down complex work

### 3. AI Integration

- **Anthropic Claude Integration**: Uses Claude API for parsing PRDs, generating tasks, and creating subtasks.
- **Perplexity AI Integration**: Optional research-backed task generation and complexity analysis.
- **Cursor AI Rules**: Custom rules in `.cursor/rules/dev_workflow.mdc` that guide the AI in understanding and working with the task management system.

### 4. Advanced Task Management Features

- **Task Complexity Analysis**: AI-driven analysis of task complexity on a scale of 1-10, with recommendations for subtask allocation.
- **Smart Task Expansion**: Breaking down complex tasks into subtasks with context-aware generation.
- **Implementation Drift Handling**: Ability to update future tasks when current implementation differs from the original plan.
- **Dependency Management**: Tools for adding, removing, validating, and fixing task dependencies.
- **Next Task Determination**: Intelligent selection of the next task based on dependencies, priority, and status.

### 5. Development Workflow Integration

- **Individual Task Files**: Generation of separate files for each task in the `tasks/` directory for easy reference.
- **Cursor Integration**: Seamless integration with Cursor AI through MCP, allowing the AI to understand and manage tasks directly.
- **Iterative Subtask Implementation**: Structured approach to implementing subtasks with logging of progress and challenges.

## Consequences

### Positive

1. **Improved Task Tracking**: More detailed and structured task management with support for subtasks, dependencies, and statuses.
2. **AI Integration**: Seamless integration with AI tools like Cursor AI, enabling more efficient AI-driven development.
3. **Complexity Management**: Better handling of complex tasks through AI-driven complexity analysis and smart task expansion.
4. **Adaptive Workflow**: Ability to handle implementation drift and update task definitions as the project evolves.
5. **Research-Backed Development**: Integration with Perplexity AI for more informed task generation and complexity analysis.
6. **Standardized Process**: Consistent approach to task management across the project, improving collaboration and knowledge sharing.
7. **Detailed Implementation Logging**: Structured approach to logging implementation details, challenges, and decisions.

### Negative

1. **Added Complexity**: The new system is more complex than the previous approach, requiring more setup and configuration.
2. **Dependencies**: Relies on external services (Anthropic Claude API, optionally Perplexity AI) which may have costs or availability concerns.
3. **Learning Curve**: Team members need to learn the new task management commands and workflow.
4. **Configuration Management**: Requires management of environment variables and API keys.
5. **Potential Overhead**: More sophisticated task management may introduce overhead for simpler tasks or smaller projects.

## References

1. [README-task-master.md](../README-task-master.md) - Main documentation for the Task Master system
2. [.cursor/rules/dev_workflow.mdc](../.cursor/rules/dev_workflow.mdc) - Cursor AI rules for the development workflow
3. [scripts/README-task-master.md](../scripts/README-task-master.md) - Detailed documentation of the meta-development script
4. [task-list.mdc](../task-list.mdc) - The original task management system