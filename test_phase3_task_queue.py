#!/usr/bin/env python3
"""
Test script for Phase 3: Task Queue Enhancement
Tests task persistence, multi-window coordination, and priority queuing
"""

import sys
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.task_queue import TaskQueue, TaskStatus, TaskType


def test_postgres_connection():
    """Test Postgres connection"""
    print("\n" + "=" * 60)
    print("Testing Postgres Connection for Task Queue")
    print("=" * 60)
    
    try:
        queue = TaskQueue()
        print("✅ TaskQueue initialized successfully")
        print(f"   Connection: {queue.connection_params['host']}:{queue.connection_params['port']}")
        print(f"   Database: {queue.connection_params['database']}")
        queue.close()
        return True
    except Exception as e:
        print(f"❌ Failed to initialize TaskQueue: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_enqueue_dequeue():
    """Test basic enqueue and dequeue operations"""
    print("\n" + "=" * 60)
    print("Testing Enqueue and Dequeue")
    print("=" * 60)
    
    try:
        with TaskQueue() as queue:
            # Enqueue a task
            task_id = queue.enqueue(
                task_type=TaskType.CHAT.value,
                data={
                    "prompt": "Test query",
                    "model": "gpt-5"
                },
                priority=5
            )
            
            print(f"✅ Task enqueued: {task_id}")
            
            # Dequeue the task
            tasks = queue.dequeue(limit=1)
            
            if len(tasks) == 1:
                task = tasks[0]
                print(f"✅ Task dequeued: {task.id}")
                print(f"   Type: {task.task_type}")
                print(f"   Priority: {task.priority}")
                print(f"   Status: {task.status}")
                print(f"   Data: {task.data}")
                
                # Clean up
                queue.cancel_task(task.id)
                
                return True
            else:
                print(f"❌ Expected 1 task, got {len(tasks)}")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_priority_ordering():
    """Test priority-based task ordering"""
    print("\n" + "=" * 60)
    print("Testing Priority Ordering")
    print("=" * 60)
    
    try:
        with TaskQueue() as queue:
            # Enqueue tasks with different priorities
            task_ids = []
            
            priorities = [3, 8, 1, 10, 5]
            for i, priority in enumerate(priorities):
                task_id = queue.enqueue(
                    task_type=TaskType.CHAT.value,
                    data={"task_number": i + 1},
                    priority=priority
                )
                task_ids.append((task_id, priority))
                print(f"   Enqueued task {i+1} with priority {priority}")
            
            # Dequeue all tasks
            dequeued_tasks = queue.dequeue(limit=5)
            
            print(f"\n✅ Dequeued {len(dequeued_tasks)} tasks")
            
            # Verify they're in priority order (highest first)
            dequeued_priorities = [task.priority for task in dequeued_tasks]
            expected_priorities = sorted(priorities, reverse=True)
            
            print(f"   Dequeued order: {dequeued_priorities}")
            print(f"   Expected order: {expected_priorities}")
            
            success = dequeued_priorities == expected_priorities
            
            if success:
                print("✅ Tasks dequeued in correct priority order")
            else:
                print("❌ Tasks not in correct priority order")
            
            # Clean up
            for task in dequeued_tasks:
                queue.cancel_task(task.id)
            
            return success
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_claim_and_status():
    """Test task claiming and status updates"""
    print("\n" + "=" * 60)
    print("Testing Task Claiming and Status Updates")
    print("=" * 60)
    
    try:
        with TaskQueue() as queue:
            # Enqueue a task
            task_id = queue.enqueue(
                task_type=TaskType.DEBUG.value,
                data={"issue": "Memory leak"},
                priority=7
            )
            
            print(f"✅ Task created: {task_id}")
            
            # Claim the task
            claimed = queue.claim_task(task_id, "window-1")
            
            if claimed:
                print(f"✅ Task claimed by window-1")
            else:
                print(f"❌ Failed to claim task")
                return False
            
            # Try to claim again (should fail)
            claimed_again = queue.claim_task(task_id, "window-2")
            
            if not claimed_again:
                print(f"✅ Duplicate claim correctly rejected")
            else:
                print(f"❌ Duplicate claim should have been rejected")
                return False
            
            # Update task to completed
            queue.update_task_status(
                task_id,
                TaskStatus.COMPLETED.value,
                result={"success": True, "output": "Bug fixed"}
            )
            
            print(f"✅ Task marked as completed")
            
            # Verify status
            task = queue.get_task(task_id)
            
            if task.status == TaskStatus.COMPLETED.value:
                print(f"✅ Task status verified: {task.status}")
                print(f"   Result: {task.result}")
                return True
            else:
                print(f"❌ Unexpected task status: {task.status}")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_multi_window_coordination():
    """Test multi-window task coordination"""
    print("\n" + "=" * 60)
    print("Testing Multi-Window Coordination")
    print("=" * 60)
    
    try:
        with TaskQueue() as queue:
            # Create tasks assigned to different windows
            task1_id = queue.enqueue(
                task_type=TaskType.CODEREVIEW.value,
                data={"file": "app.py"},
                assigned_to="window-1",
                priority=5
            )
            
            task2_id = queue.enqueue(
                task_type=TaskType.CONSENSUS.value,
                data={"question": "Which approach?"},
                assigned_to="window-2",
                priority=8
            )
            
            task3_id = queue.enqueue(
                task_type=TaskType.CHAT.value,
                data={"prompt": "Unassigned task"},
                assigned_to=None,
                priority=6
            )
            
            print(f"✅ Created 3 tasks (2 assigned, 1 unassigned)")
            
            # Window 1 dequeues (should get task1 and task3)
            window1_tasks = queue.dequeue(agent_id="window-1", limit=5)
            window1_ids = [t.id for t in window1_tasks]
            
            print(f"\n   Window 1 sees {len(window1_tasks)} tasks:")
            for task in window1_tasks:
                print(f"     - {task.id} (assigned_to={task.assigned_to}, priority={task.priority})")
            
            # Window 2 dequeues (should get task2 and task3)
            window2_tasks = queue.dequeue(agent_id="window-2", limit=5)
            window2_ids = [t.id for t in window2_tasks]
            
            print(f"\n   Window 2 sees {len(window2_tasks)} tasks:")
            for task in window2_tasks:
                print(f"     - {task.id} (assigned_to={task.assigned_to}, priority={task.priority})")
            
            # Verify assignments
            success = True
            
            if task1_id in window1_ids and task1_id not in window2_ids:
                print(f"\n✅ Task 1 correctly visible to window-1 only")
            else:
                print(f"\n❌ Task 1 assignment incorrect")
                success = False
            
            if task2_id in window2_ids and task2_id not in window1_ids:
                print(f"✅ Task 2 correctly visible to window-2 only")
            else:
                print(f"❌ Task 2 assignment incorrect")
                success = False
            
            if task3_id in window1_ids and task3_id in window2_ids:
                print(f"✅ Unassigned task visible to both windows")
            else:
                print(f"❌ Unassigned task should be visible to both")
                success = False
            
            # Clean up
            for task_id in [task1_id, task2_id, task3_id]:
                queue.cancel_task(task_id)
            
            return success
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_persistence():
    """Test task persistence across restarts"""
    print("\n" + "=" * 60)
    print("Testing Task Persistence")
    print("=" * 60)
    
    try:
        # Create and enqueue task
        task_id = None
        with TaskQueue() as queue:
            task_id = queue.enqueue(
                task_type=TaskType.PLANNER.value,
                data={"plan": "New architecture"},
                priority=7
            )
            print(f"✅ Task created: {task_id}")
        
        print(f"   Queue closed (simulating restart)")
        
        # Reopen and verify task still exists
        time.sleep(0.5)  # Small delay to simulate restart
        
        with TaskQueue() as queue:
            task = queue.get_task(task_id)
            
            if task:
                print(f"✅ Task persisted across restart")
                print(f"   ID: {task.id}")
                print(f"   Type: {task.task_type}")
                print(f"   Priority: {task.priority}")
                print(f"   Data: {task.data}")
                
                # Clean up
                queue.cancel_task(task.id)
                
                return True
            else:
                print(f"❌ Task not found after restart")
                return False
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_statistics():
    """Test task statistics"""
    print("\n" + "=" * 60)
    print("Testing Task Statistics")
    print("=" * 60)
    
    try:
        with TaskQueue() as queue:
            # Create various tasks
            task_ids = []
            
            # Pending tasks
            for i in range(3):
                task_id = queue.enqueue(
                    task_type=TaskType.CHAT.value,
                    data={"num": i},
                    priority=5
                )
                task_ids.append(task_id)
            
            # Running task
            running_task_id = queue.enqueue(
                task_type=TaskType.DEBUG.value,
                data={"issue": "test"},
                priority=8
            )
            queue.claim_task(running_task_id, "window-1")
            task_ids.append(running_task_id)
            
            # Completed task
            completed_task_id = queue.enqueue(
                task_type=TaskType.CODEREVIEW.value,
                data={"file": "test.py"},
                priority=6
            )
            queue.update_task_status(completed_task_id, TaskStatus.COMPLETED.value)
            task_ids.append(completed_task_id)
            
            # Get statistics
            stats = queue.get_task_stats()
            
            print(f"✅ Statistics retrieved:")
            print(f"   Total pending: {stats['total_pending']}")
            print(f"   Total running: {stats['total_running']}")
            print(f"   Total completed: {stats['total_completed']}")
            print(f"   Status counts: {stats['status_counts']}")
            print(f"   Type counts: {stats['type_counts']}")
            print(f"   Avg wait time: {stats['avg_wait_seconds']:.2f}s")
            
            # Verify counts
            success = (
                stats['total_pending'] >= 3 and
                stats['total_running'] >= 1 and
                stats['total_completed'] >= 1
            )
            
            if success:
                print(f"\n✅ Statistics correct")
            else:
                print(f"\n❌ Statistics incorrect")
            
            # Clean up
            for task_id in task_ids:
                try:
                    task = queue.get_task(task_id)
                    if task and task.status not in [TaskStatus.COMPLETED.value, TaskStatus.CANCELLED.value]:
                        queue.cancel_task(task_id)
                except:
                    pass
            
            return success
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_task_cleanup():
    """Test old task cleanup"""
    print("\n" + "=" * 60)
    print("Testing Task Cleanup")
    print("=" * 60)
    
    try:
        with TaskQueue() as queue:
            # Create and complete a task
            task_id = queue.enqueue(
                task_type=TaskType.CHAT.value,
                data={"test": "cleanup"},
                priority=5
            )
            
            queue.update_task_status(task_id, TaskStatus.COMPLETED.value)
            
            print(f"✅ Created completed task: {task_id}")
            
            # Cleanup (won't delete recent tasks, just testing the function)
            deleted = queue.cleanup_old_tasks(days=7)
            
            print(f"✅ Cleanup function executed")
            print(f"   Deleted {deleted} old tasks")
            
            return True
    
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Run all Phase 3 tests"""
    print("\n" + "=" * 60)
    print("PHASE 3 TASK QUEUE TESTS")
    print("Task 8: Agent-Fusion Integration")
    print("=" * 60)
    
    results = {}
    
    # Test 1: Postgres connection
    results['postgres_connection'] = test_postgres_connection()
    
    # Test 2: Enqueue/dequeue
    results['enqueue_dequeue'] = test_task_enqueue_dequeue()
    
    # Test 3: Priority ordering
    results['priority_ordering'] = test_priority_ordering()
    
    # Test 4: Task claiming and status
    results['claim_and_status'] = test_task_claim_and_status()
    
    # Test 5: Multi-window coordination
    results['multi_window'] = test_multi_window_coordination()
    
    # Test 6: Task persistence
    results['persistence'] = test_task_persistence()
    
    # Test 7: Statistics
    results['statistics'] = test_task_statistics()
    
    # Test 8: Cleanup
    results['cleanup'] = test_task_cleanup()
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    all_passed = all(results.values())
    passed_count = sum(results.values())
    total_count = len(results)
    
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print("=" * 60)
    
    if all_passed:
        print(f"\n🎉 All Phase 3 tests passed! ({passed_count}/{total_count})")
        print("\n✅ Phase 3 Success Criteria Met:")
        print("   ✅ Postgres task_queue working")
        print("   ✅ Tasks persist across restarts")
        print("   ✅ Multiple windows can coordinate")
        print("   ✅ Priority ordering works")
        print("   ✅ Status transitions tracked")
        print("\nNext step: Phase 4 - Enhanced Voting")
        return 0
    else:
        print(f"\n⚠️  Some tests failed ({passed_count}/{total_count} passed)")
        print("Please review the output above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

