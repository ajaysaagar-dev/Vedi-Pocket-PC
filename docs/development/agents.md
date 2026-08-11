# Agent Directives & Behavior Guidelines

## Autonomous Execution Policy
- **Never ask for permission** before creating, writing, editing, or modifying any files (`write_to_file`, `replace_file_content`, `multi_replace_file_content`).
- **Never ask for permission** before executing terminal commands or scripts (`run_command`).
- **Execute tools immediately and autonomously**: For all coding tasks, file creations, refactoring, package installations, and verification steps, proceed directly without prompting the user for approval.
