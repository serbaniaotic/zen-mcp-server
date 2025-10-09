# Context7 Integration - Agent Instructions

## Overview

Context7 is integrated into the zen-mcp stack to provide agents with real-time access to API schemas, endpoint documentation, and type definitions. Use Context7 whenever you need to discover or verify API endpoints, parameter schemas, or authentication patterns.

## When to Use Context7

### Primary Use Cases
1. **API Schema Discovery** - Finding endpoints, request/response schemas
2. **Type Definitions** - Getting TypeScript/Python type definitions
3. **Authentication Patterns** - Looking up auth flows and token formats
4. **Parameter Documentation** - Discovering required/optional parameters
5. **Version-Specific APIs** - Checking for breaking changes between versions

### Examples of When to Use
- "What endpoints does the Notion API have for creating pages?"
- "What's the schema for Stripe's payment intent creation?"
- "What parameters does the GitHub API accept for creating issues?"
- "How do I authenticate with the OpenAI API?"
- "What's the latest React Hook API?"

## How to Use the Context7 Tool

The `context7` tool has three main actions:

### 1. Resolve Library ID
First, convert a library name to its Context7 library ID:

```json
{
  "action": "resolve-library",
  "library_name": "notion"
}
```

Common libraries:
- `notion` - Notion API
- `stripe` - Stripe API
- `github` - GitHub REST API
- `openai` - OpenAI API
- `react` - React library
- `typescript` - TypeScript definitions

### 2. Search Documentation
Once you have the library ID, search for specific documentation:

```json
{
  "action": "search-docs",
  "library_id": "notion-api",
  "query": "create page endpoint"
}
```

### 3. Get Schema
Retrieve API schema information:

```json
{
  "action": "get-schema",
  "library_id": "stripe-api",
  "query": "payment intent"
}
```

## Typical Workflow

### Example: Discovering Notion API Schema

```python
# Step 1: Resolve the library name
result = await context7_tool.run({
    "action": "resolve-library",
    "library_name": "notion"
})
# Response includes library_id: "notion-api"

# Step 2: Search for specific endpoint
result = await context7_tool.run({
    "action": "search-docs",
    "library_id": "notion-api",
    "query": "pages create"
})
# Response includes endpoint schema, parameters, examples

# Step 3: Get detailed schema if needed
result = await context7_tool.run({
    "action": "get-schema",
    "library_id": "notion-api",
    "query": "page properties schema"
})
```

## Integration with Other Tools

### Combined with `apilookup` Tool
- Use `context7` for schema discovery
- Use `apilookup` for current version info and breaking changes
- Combine both for complete API understanding

### Combined with `thinkdeep` Tool
When investigating API integration issues:
1. Use `thinkdeep` to analyze the problem
2. Use `context7` to verify correct schema/endpoints
3. Use `thinkdeep` again to synthesize solution

### Combined with `chat` Tool
For interactive exploration:
1. Use `chat` to discuss API design approach
2. Use `context7` to look up exact schemas
3. Use `chat` to validate implementation strategy

## Best Practices

### Do's
✅ Always resolve library ID first before searching
✅ Use specific queries for better results
✅ Check schema when implementing new API integrations
✅ Use Context7 to validate existing code against latest docs
✅ Combine with other tools for comprehensive analysis

### Don'ts
❌ Don't guess library IDs - always use resolve-library
❌ Don't skip Context7 when working with external APIs
❌ Don't use generic queries - be specific
❌ Don't assume schemas - always verify with Context7

## Common Scenarios

### Scenario 1: Implementing New API Integration
```
Agent Task: "Implement Notion database query endpoint"

Workflow:
1. Use context7 to resolve "notion" library
2. Use context7 to search "database query endpoint"
3. Review schema from Context7
4. Use codereview to check implementation
5. Use context7 to verify all required parameters
```

### Scenario 2: Debugging API Call Failures
```
Agent Task: "Fix failing Stripe payment creation"

Workflow:
1. Use debug to analyze the error
2. Use context7 to verify correct Stripe schema
3. Compare implementation against Context7 schema
4. Use context7 to check authentication requirements
5. Apply fix and validate
```

### Scenario 3: API Version Migration
```
Agent Task: "Migrate from Notion API v1 to v2"

Workflow:
1. Use context7 to get v1 schema
2. Use context7 to get v2 schema
3. Use planner to create migration strategy
4. Use codereview to validate changes
5. Use context7 to verify all endpoints updated
```

## Error Handling

If Context7 query fails:
1. Check that context7-mcp-server is running: `docker ps | grep context7`
2. Verify library name is correct (try common variations)
3. Check network connectivity between containers
4. Review Context7 logs: `docker logs context7-mcp-server`

## Performance Notes

- Context7 queries are fast (<1s typically)
- Results are cached by Context7 for repeated queries
- Use specific queries to reduce response size
- Library resolution is one-time per library

## Integration Status

- ✅ Context7 MCP server running in docker
- ✅ context7 tool registered in zen-mcp
- ✅ Network connectivity configured
- ✅ Available to all zen-mcp agents (chat, thinkdeep, debug, codereview, etc.)

## Support

For issues with Context7:
- Check docker logs: `docker logs context7-mcp-server`
- Verify container health: `docker ps | grep context7`
- Review this document for correct usage patterns
- Check Context7 GitHub: https://github.com/iflow-mcp/context7-mcp
