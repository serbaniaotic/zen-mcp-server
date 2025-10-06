# GitHub Copilot Chat + Zen MCP Integration

Zen MCP tools are now available in **both** Claude Code and GitHub Copilot Chat!

## Quick Start

### 1. Enable Agent Mode in Copilot Chat

In the Copilot Chat panel (Ctrl+Alt+I):
1. Click the **"Tools"** button (or use `@workspace` mode)
2. Enable Zen tools from the tools list
3. Start chatting!

### 2. Using Zen Tools in Copilot

**Direct invocation:**
```
Use zen:project_switch to switch to toolbox
```

**With context:**
```
@workspace #zen:chat_smart Ask Gemini to explain this file
```

**In conversation:**
```
Can you use the project_switch tool to navigate to the motif project?
```

## Available Zen Tools in Copilot

### Core Tools
- `chat` - Multi-model AI chat (Claude, Gemini, GPT-4)
- `chat_smart` - Automatic provider routing based on limits
- `project_switch` - Navigate Tâm Đắc projects (cross-platform!)
- `thinkdeep` - Deep reasoning mode
- `consensus` - Multi-model consensus
- `planner` - Task planning
- `version` - Check Zen version

### Code Tools
- `analyze` - Code analysis
- `codereview` - Code review
- `debug` - Debug assistance
- `refactor` - Refactoring suggestions
- `testgen` - Generate tests
- `docgen` - Generate documentation

## Slash Command Mapping

Your `.claude/commands/*.md` files don't directly work in Copilot, but you can:

### Option 1: Use Zen Tools (Recommended)
Instead of `/project`, use Copilot + Zen:
```
Use project_switch with project=toolbox section=tickets
```

### Option 2: Create VSCode Tasks
Map commands to tasks in `.vscode/tasks.json`:
```json
{
  "label": "/project",
  "command": "mcp-invoke",
  "args": ["zen", "project_switch", "${input:project}"]
}
```

### Option 3: Use Copilot's Built-in Slash Commands
```
/explain - Explain code
/fix - Suggest fixes
/tests - Generate tests
/doc - Generate documentation
```

## Configuration

### Workspace-level (team shared)
File: `.vscode/mcp.json`
```json
{
  "mcpServers": {
    "zen": {
      "command": "/path/to/.zen_venv/bin/python",
      "args": ["/path/to/server.py"],
      "env": {
        "GEMINI_API_KEY": "${env:GEMINI_API_KEY}",
        "OPENAI_API_KEY": "${env:OPENAI_API_KEY}"
      }
    }
  }
}
```

### User-level (personal)
Already configured via `claude mcp add zen` ✅

## Tool Management

### Enable/Disable Tools
Click **Tools** button in Copilot Chat → Toggle tools on/off

### Tool Limits
- Max 128 tools per request (model constraint)
- Group related tools into tool sets

## Advanced: Create Tool Sets

Group frequently used tools:
```json
{
  "toolSets": {
    "tamdac-dev": {
      "tools": [
        "zen:project_switch",
        "zen:chat_smart",
        "zen:consensus"
      ]
    }
  }
}
```

Then use: `@workspace #tamdac-dev`

## Debugging

### Check MCP Connection
```bash
claude mcp list
```

### View Tool Schema
Open Copilot Chat → Tools → Click tool name → View schema

### Logs
- Zen logs: `zen-mcp-server/logs/mcp_server.log`
- Copilot logs: Output panel → "GitHub Copilot"

## Examples

### Switch Project and Analyze Code
```
Use project_switch to go to motif, then use analyze to check server.ts
```

### Smart Chat with Gemini (save Claude limits)
```
Use chat_smart with provider=gemini to explain how the RAG system works
```

### Multi-Model Consensus
```
Use consensus to get opinions from Claude, Gemini, and GPT-4 on the best architecture
```

## Tips

1. **Save Claude limits**: Use `chat_smart` or specify `provider=gemini` in chat
2. **Cross-platform**: Same tools work in Claude Code + Copilot + Cursor!
3. **Agent mode**: Always enable agent mode for MCP tool access
4. **Context**: Use `#zen:tool_name` syntax for better context awareness

## Troubleshooting

**Tools not showing up?**
- Restart VSCode
- Check `.vscode/mcp.json` exists
- Verify Zen is running: `claude mcp list`

**Permission errors?**
- Check file paths in mcp.json
- Verify Python venv is activated
- Check API keys in environment

**Slash commands not working?**
- Copilot uses different slash commands than Claude Code
- Use tool invocation syntax instead: `Use tool_name ...`
