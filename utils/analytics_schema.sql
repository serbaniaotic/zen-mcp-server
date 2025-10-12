-- Analytics schema for DuckDB
-- Tracks tool executions, routing decisions, and model performance

-- Tool execution tracking
CREATE TABLE IF NOT EXISTS tool_executions (
    id VARCHAR PRIMARY KEY,
    tool_name VARCHAR NOT NULL,
    model VARCHAR,
    status VARCHAR NOT NULL,
    tokens_used INTEGER,
    execution_time_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Routing decisions tracking
CREATE TABLE IF NOT EXISTS routing_decisions (
    id VARCHAR PRIMARY KEY,
    user_intent TEXT,
    detected_complexity INTEGER,
    detected_risk INTEGER,
    chosen_tool VARCHAR,
    chosen_strategy VARCHAR,
    outcome VARCHAR,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSON
);

-- Model performance aggregations
CREATE TABLE IF NOT EXISTS model_performance (
    id VARCHAR PRIMARY KEY,
    tool_name VARCHAR,
    model VARCHAR,
    success_rate FLOAT,
    avg_tokens INTEGER,
    avg_time_ms INTEGER,
    sample_size INTEGER,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tool_executions_tool ON tool_executions(tool_name);
CREATE INDEX IF NOT EXISTS idx_tool_executions_model ON tool_executions(model);
CREATE INDEX IF NOT EXISTS idx_tool_executions_created ON tool_executions(created_at);
CREATE INDEX IF NOT EXISTS idx_tool_executions_success ON tool_executions(success);

CREATE INDEX IF NOT EXISTS idx_routing_tool ON routing_decisions(chosen_tool);
CREATE INDEX IF NOT EXISTS idx_routing_strategy ON routing_decisions(chosen_strategy);
CREATE INDEX IF NOT EXISTS idx_routing_created ON routing_decisions(created_at);

CREATE INDEX IF NOT EXISTS idx_model_perf_tool ON model_performance(tool_name);
CREATE INDEX IF NOT EXISTS idx_model_perf_model ON model_performance(model);

-- Views for common analytics queries

-- Success rate by tool and model
CREATE VIEW IF NOT EXISTS v_success_rate_by_tool_model AS
SELECT 
    tool_name,
    model,
    COUNT(*) as total_executions,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as successful_executions,
    CAST(SUM(CASE WHEN success THEN 1 ELSE 0 END) AS FLOAT) / COUNT(*) as success_rate,
    AVG(tokens_used) as avg_tokens,
    AVG(execution_time_ms) as avg_time_ms
FROM tool_executions
GROUP BY tool_name, model;

-- Recent routing decisions
CREATE VIEW IF NOT EXISTS v_recent_routing AS
SELECT 
    id,
    user_intent,
    detected_complexity,
    detected_risk,
    chosen_tool,
    chosen_strategy,
    outcome,
    created_at
FROM routing_decisions
ORDER BY created_at DESC
LIMIT 100;

-- Tool usage summary (last 7 days)
CREATE VIEW IF NOT EXISTS v_tool_usage_7d AS
SELECT 
    tool_name,
    COUNT(*) as execution_count,
    SUM(CASE WHEN success THEN 1 ELSE 0 END) as success_count,
    AVG(execution_time_ms) as avg_execution_time,
    SUM(tokens_used) as total_tokens
FROM tool_executions
WHERE created_at >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY tool_name
ORDER BY execution_count DESC;

