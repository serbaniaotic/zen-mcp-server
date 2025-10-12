-- Task Queue Schema for Postgres
-- Used for persistent task management and multi-window coordination

CREATE TABLE IF NOT EXISTS task_queue (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    task_type VARCHAR NOT NULL, -- 'consensus', 'thinkdeep', 'debug', 'codereview', etc.
    status VARCHAR NOT NULL DEFAULT 'pending', -- 'pending', 'running', 'completed', 'failed'
    assigned_to VARCHAR, -- agent/window ID
    priority INTEGER DEFAULT 5, -- 1 (lowest) to 10 (highest)
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP,
    data JSONB NOT NULL, -- Task parameters and context
    result JSONB -- Task execution result
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_task_status ON task_queue(status);
CREATE INDEX IF NOT EXISTS idx_task_assigned ON task_queue(assigned_to);
CREATE INDEX IF NOT EXISTS idx_task_priority ON task_queue(priority DESC, created_at ASC);
CREATE INDEX IF NOT EXISTS idx_task_created ON task_queue(created_at);

-- Function to automatically update updated_at timestamp
CREATE OR REPLACE FUNCTION update_task_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to automatically update updated_at
CREATE TRIGGER task_queue_updated_at
    BEFORE UPDATE ON task_queue
    FOR EACH ROW
    EXECUTE FUNCTION update_task_updated_at();

-- View for pending tasks
CREATE OR REPLACE VIEW v_pending_tasks AS
SELECT 
    id,
    task_type,
    assigned_to,
    priority,
    created_at,
    data
FROM task_queue
WHERE status = 'pending'
ORDER BY priority DESC, created_at ASC;

-- View for task statistics
CREATE OR REPLACE VIEW v_task_stats AS
SELECT 
    task_type,
    status,
    COUNT(*) as task_count,
    AVG(EXTRACT(EPOCH FROM (completed_at - created_at))) as avg_duration_seconds
FROM task_queue
WHERE completed_at IS NOT NULL
GROUP BY task_type, status;

