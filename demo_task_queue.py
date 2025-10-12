#!/usr/bin/env python3
"""
Demo script for Task Queue in Zen MCP Server.
Shows how to use the persistent task queue for multi-window coordination.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.task_queue import TaskQueue, TaskStatus, TaskType


def demo_basic_queue_operations():
    """Demo basic queue operations"""
    print("\n" + "=" * 70)
    print("DEMO 1: Basic Queue Operations")
    print("=" * 70)
    
    with TaskQueue() as queue:
        print("\n📝 Enqueueing tasks...")
        
        # Enqueue various tasks
        task1 = queue.enqueue(
            task_type=TaskType.CHAT.value,
            data={"prompt": "Explain Python decorators", "model": "gpt-5"},
            priority=5
        )
        print(f"   ✅ Task 1: Chat (priority 5)")
        
        task2 = queue.enqueue(
            task_type=TaskType.DEBUG.value,
            data={"issue": "Memory leak in server", "severity": "high"},
            priority=8
        )
        print(f"   ✅ Task 2: Debug (priority 8)")
        
        task3 = queue.enqueue(
            task_type=TaskType.CODEREVIEW.value,
            data={"files": ["auth.py", "api.py"], "focus": "security"},
            priority=10
        )
        print(f"   ✅ Task 3: Code Review (priority 10)")
        
        print("\n📥 Dequeueing tasks (priority order)...")
        
        # Dequeue all tasks
        tasks = queue.dequeue(limit=3)
        
        for i, task in enumerate(tasks, 1):
            print(f"\n   Task {i} (Priority {task.priority}):")
            print(f"   - ID: {task.id}")
            print(f"   - Type: {task.task_type}")
            print(f"   - Data: {task.data}")
        
        # Clean up
        for task in tasks:
            queue.cancel_task(task.id)


def demo_multi_window_coordination():
    """Demo multi-window coordination"""
    print("\n" + "=" * 70)
    print("DEMO 2: Multi-Window Coordination")
    print("=" * 70)
    
    with TaskQueue() as queue:
        print("\n📝 Creating tasks for different windows...")
        
        # Window 1 tasks
        task1 = queue.enqueue(
            task_type=TaskType.PLANNER.value,
            data={"plan": "Design new API"},
            assigned_to="window-1",
            priority=7
        )
        print(f"   ✅ Task assigned to window-1")
        
        # Window 2 tasks
        task2 = queue.enqueue(
            task_type=TaskType.CONSENSUS.value,
            data={"question": "Which database to use?"},
            assigned_to="window-2",
            priority=9
        )
        print(f"   ✅ Task assigned to window-2")
        
        # Shared task (no assignment)
        task3 = queue.enqueue(
            task_type=TaskType.CHAT.value,
            data={"prompt": "General question"},
            assigned_to=None,
            priority=5
        )
        print(f"   ✅ Shared task (no assignment)")
        
        print("\n👀 Window 1 view:")
        window1_tasks = queue.dequeue(agent_id="window-1", limit=10)
        for task in window1_tasks:
            print(f"   - {task.task_type} (priority {task.priority}, assigned_to={task.assigned_to})")
        
        print("\n👀 Window 2 view:")
        window2_tasks = queue.dequeue(agent_id="window-2", limit=10)
        for task in window2_tasks:
            print(f"   - {task.task_type} (priority {task.priority}, assigned_to={task.assigned_to})")
        
        print("\n💡 Key insight: Unassigned tasks visible to all windows!")
        
        # Clean up
        for task_id in [task1, task2, task3]:
            queue.cancel_task(task_id)


def demo_task_lifecycle():
    """Demo complete task lifecycle"""
    print("\n" + "=" * 70)
    print("DEMO 3: Task Lifecycle")
    print("=" * 70)
    
    with TaskQueue() as queue:
        print("\n1️⃣  Creating task...")
        
        task_id = queue.enqueue(
            task_type=TaskType.THINKDEEP.value,
            data={
                "question": "Investigate performance bottleneck",
                "complexity": 8
            },
            priority=7
        )
        print(f"   ✅ Task created: {task_id}")
        
        task = queue.get_task(task_id)
        print(f"   Status: {task.status}")
        
        print("\n2️⃣  Claiming task (window-1)...")
        
        claimed = queue.claim_task(task_id, "window-1")
        
        if claimed:
            print(f"   ✅ Task claimed by window-1")
            task = queue.get_task(task_id)
            print(f"   Status: {task.status}")
            print(f"   Assigned to: {task.assigned_to}")
        
        print("\n3️⃣  Simulating work...")
        time.sleep(1)
        print(f"   ... analyzing performance ...")
        time.sleep(1)
        print(f"   ... found bottleneck ...")
        
        print("\n4️⃣  Completing task...")
        
        queue.update_task_status(
            task_id,
            TaskStatus.COMPLETED.value,
            result={
                "bottleneck": "Database query N+1 problem",
                "solution": "Add eager loading",
                "estimated_speedup": "10x"
            }
        )
        print(f"   ✅ Task completed")
        
        task = queue.get_task(task_id)
        print(f"   Status: {task.status}")
        print(f"   Result: {task.result}")


def demo_task_persistence():
    """Demo task persistence across restarts"""
    print("\n" + "=" * 70)
    print("DEMO 4: Task Persistence (Simulated Restart)")
    print("=" * 70)
    
    # Create tasks
    task_ids = []
    print("\n1️⃣  Creating tasks...")
    
    with TaskQueue() as queue:
        for i in range(3):
            task_id = queue.enqueue(
                task_type=TaskType.CHAT.value,
                data={"task_number": i + 1},
                priority=5 + i
            )
            task_ids.append(task_id)
            print(f"   ✅ Task {i+1} created")
    
    print(f"\n   🔄 Closing queue (simulating server restart)...")
    time.sleep(1)
    
    # Reopen and verify
    print(f"\n2️⃣  Reopening queue (after restart)...")
    
    with TaskQueue() as queue:
        print(f"   ✅ Queue reopened")
        
        print(f"\n   📋 Checking for persisted tasks...")
        
        pending = queue.get_pending_tasks()
        
        print(f"   Found {len(pending)} pending tasks:")
        
        for task in pending:
            if task.id in task_ids:
                print(f"   ✅ Task {task.data['task_number']} still exists (priority {task.priority})")
        
        print(f"\n💡 All tasks survived the restart!")
        
        # Clean up
        for task_id in task_ids:
            queue.cancel_task(task_id)


def demo_priority_and_stats():
    """Demo priority queuing and statistics"""
    print("\n" + "=" * 70)
    print("DEMO 5: Priority Queuing & Statistics")
    print("=" * 70)
    
    with TaskQueue() as queue:
        print("\n📝 Creating tasks with various priorities...")
        
        priorities = [
            (TaskType.CHAT.value, 3, "Low priority question"),
            (TaskType.DEBUG.value, 7, "Bug fix needed"),
            (TaskType.CONSENSUS.value, 10, "Critical decision"),
            (TaskType.CODEREVIEW.value, 5, "Review PR"),
            (TaskType.THINKDEEP.value, 9, "Urgent investigation"),
        ]
        
        task_ids = []
        for task_type, priority, description in priorities:
            task_id = queue.enqueue(
                task_type=task_type,
                data={"description": description},
                priority=priority
            )
            task_ids.append(task_id)
            print(f"   - {task_type} (priority {priority}): {description}")
        
        print("\n📊 Task Statistics:")
        
        stats = queue.get_task_stats()
        
        print(f"   Total pending: {stats['total_pending']}")
        print(f"   Total running: {stats['total_running']}")
        print(f"   Total completed: {stats['total_completed']}")
        print(f"   Average wait time: {stats['avg_wait_seconds']:.2f}s")
        
        print("\n📥 Dequeuing in priority order:")
        
        tasks = queue.dequeue(limit=5)
        
        for i, task in enumerate(tasks, 1):
            print(f"   {i}. {task.task_type} (priority {task.priority})")
        
        print("\n💡 Higher priority tasks dequeued first!")
        
        # Clean up
        for task_id in task_ids:
            queue.cancel_task(task_id)


def demo_practical_workflow():
    """Demo a practical multi-step workflow"""
    print("\n" + "=" * 70)
    print("DEMO 6: Practical Multi-Step Workflow")
    print("=" * 70)
    
    print("\n📋 Scenario: Deploy new feature to production")
    print("   Creating workflow tasks...\n")
    
    with TaskQueue() as queue:
        workflow_tasks = [
            (TaskType.CODEREVIEW.value, 10, "Step 1: Review code changes", "window-1"),
            (TaskType.PRECOMMIT.value, 9, "Step 2: Validate git changes", "window-1"),
            (TaskType.DEBUG.value, 8, "Step 3: Run integration tests", "window-2"),
            (TaskType.CONSENSUS.value, 10, "Step 4: Approve deployment", None),
            (TaskType.CHAT.value, 7, "Step 5: Generate deployment docs", "window-2"),
        ]
        
        task_ids = []
        for task_type, priority, description, assigned_to in workflow_tasks:
            task_id = queue.enqueue(
                task_type=task_type,
                data={"workflow_step": description},
                assigned_to=assigned_to,
                priority=priority
            )
            task_ids.append(task_id)
            
            assignment = f"→ {assigned_to}" if assigned_to else "→ any window"
            print(f"   ✅ {description} {assignment}")
        
        print("\n👥 Task distribution:")
        print("\n   Window 1 tasks:")
        window1_tasks = queue.get_pending_tasks(agent_id="window-1")
        for task in window1_tasks:
            print(f"   - {task.data['workflow_step']}")
        
        print("\n   Window 2 tasks:")
        window2_tasks = queue.get_pending_tasks(agent_id="window-2")
        for task in window2_tasks:
            print(f"   - {task.data['workflow_step']}")
        
        print("\n   Shared tasks (any window can take):")
        shared_tasks = [t for t in queue.get_pending_tasks() if not t.assigned_to]
        for task in shared_tasks:
            print(f"   - {task.data['workflow_step']}")
        
        print("\n💡 Tasks can be distributed across multiple windows for parallel work!")
        
        # Clean up
        for task_id in task_ids:
            queue.cancel_task(task_id)


def main():
    """Run all demos"""
    print("\n" + "=" * 70)
    print("TASK QUEUE DEMONSTRATION")
    print("Zen MCP Server - Phase 3")
    print("=" * 70)
    
    try:
        demo_basic_queue_operations()
        demo_multi_window_coordination()
        demo_task_lifecycle()
        demo_task_persistence()
        demo_priority_and_stats()
        demo_practical_workflow()
        
        print("\n" + "=" * 70)
        print("✅ All demos completed successfully!")
        print("=" * 70)
        
        print("\n💡 Key Features:")
        print("   ✅ Tasks persist across restarts")
        print("   ✅ Multi-window coordination")
        print("   ✅ Priority-based queuing")
        print("   ✅ Task status tracking")
        print("   ✅ Atomic task claiming")
        print("   ✅ Statistics and monitoring")
        
        print("\n📚 Usage Example:")
        print("   ")
        print("   from utils.task_queue import TaskQueue, TaskType")
        print("   ")
        print("   with TaskQueue() as queue:")
        print("       # Enqueue task")
        print("       task_id = queue.enqueue(")
        print("           task_type=TaskType.CHAT.value,")
        print("           data={'prompt': 'Your question'},")
        print("           priority=7")
        print("       )")
        print("       ")
        print("       # Dequeue task")
        print("       tasks = queue.dequeue(limit=1)")
        print("       ")
        print("       # Process and complete")
        print("       queue.claim_task(task_id, 'window-1')")
        print("       queue.update_task_status(task_id, 'completed')")
        print("")
        
        return 0
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())

