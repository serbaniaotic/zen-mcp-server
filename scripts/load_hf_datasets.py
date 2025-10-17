#!/usr/bin/env python3
"""
Load HuggingFace Datasets into SmartMemoryAPI

Loads reasoning datasets (HotpotQA, MuSiQue) into smartmemoryapi for
dataset_rag tool to query via semantic search.

Usage:
    python scripts/load_hf_datasets.py --dataset hotpotqa --limit 100
    python scripts/load_hf_datasets.py --dataset musique --limit 50
    python scripts/load_hf_datasets.py --dataset all --limit 200
"""

import asyncio
import argparse
import logging
from typing import List, Dict, Any
import httpx

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# SmartMemoryAPI endpoint
SMARTMEMORY_URL = "http://localhost:8099"


async def load_hotpotqa(limit: int = 100) -> int:
    """
    Load HotpotQA dataset into smartmemoryapi

    HotpotQA: Multi-hop reasoning dataset with supporting facts
    https://huggingface.co/datasets/hotpot_qa

    Args:
        limit: Number of examples to load

    Returns:
        Number of examples successfully loaded
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets library not installed. Run: pip install datasets")
        return 0

    logger.info(f"Loading HotpotQA dataset (limit: {limit})...")

    # Load dataset from HuggingFace
    try:
        dataset = load_dataset("hotpot_qa", "distractor", split="train")
    except Exception as e:
        logger.error(f"Failed to load HotpotQA: {e}")
        return 0

    loaded_count = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, example in enumerate(dataset):
            if i >= limit:
                break

            try:
                # Prepare memory
                question = example['question']
                answer = example['answer']
                supporting_facts = example.get('supporting_facts', {})
                question_type = example.get('type', 'unknown')

                # Add to smartmemoryapi
                response = await client.post(
                    f"{SMARTMEMORY_URL}/add",
                    json={
                        "user_message": question,
                        "user_id": "datasets",  # Namespace for HF datasets
                        "agent_id": "dataset_loader",
                        "metadata": {
                            "dataset": "hotpotqa",
                            "answer": answer,
                            "type": question_type,
                            "supporting_facts": supporting_facts,
                            "index": i
                        }
                    }
                )

                if response.status_code == 200:
                    loaded_count += 1
                    if (i + 1) % 10 == 0:
                        logger.info(f"  Loaded {i + 1}/{limit} HotpotQA examples...")
                else:
                    logger.warning(f"  Failed to load example {i}: {response.status_code}")

            except Exception as e:
                logger.warning(f"  Error loading example {i}: {e}")
                continue

    logger.info(f"✅ Loaded {loaded_count} HotpotQA examples into smartmemoryapi")
    return loaded_count


async def load_musique(limit: int = 50) -> int:
    """
    Load MuSiQue dataset into smartmemoryapi

    MuSiQue: Multi-hop question answering with complex reasoning chains
    https://huggingface.co/datasets/musique

    Args:
        limit: Number of examples to load

    Returns:
        Number of examples successfully loaded
    """
    try:
        from datasets import load_dataset
    except ImportError:
        logger.error("datasets library not installed. Run: pip install datasets")
        return 0

    logger.info(f"Loading MuSiQue dataset (limit: {limit})...")

    # Load dataset from HuggingFace
    try:
        dataset = load_dataset("musique", "musique_ans_v1.0", split="train")
    except Exception as e:
        logger.error(f"Failed to load MuSiQue: {e}")
        return 0

    loaded_count = 0
    async with httpx.AsyncClient(timeout=30.0) as client:
        for i, example in enumerate(dataset):
            if i >= limit:
                break

            try:
                # Prepare memory
                question = example['question']
                answer = example.get('answer', '')
                paragraphs = example.get('paragraphs', [])
                question_type = example.get('question_decomposition', 'unknown')

                # Add to smartmemoryapi
                response = await client.post(
                    f"{SMARTMEMORY_URL}/add",
                    json={
                        "user_message": question,
                        "user_id": "datasets",
                        "agent_id": "dataset_loader",
                        "metadata": {
                            "dataset": "musique",
                            "answer": answer,
                            "type": question_type,
                            "paragraphs_count": len(paragraphs),
                            "index": i
                        }
                    }
                )

                if response.status_code == 200:
                    loaded_count += 1
                    if (i + 1) % 10 == 0:
                        logger.info(f"  Loaded {i + 1}/{limit} MuSiQue examples...")
                else:
                    logger.warning(f"  Failed to load example {i}: {response.status_code}")

            except Exception as e:
                logger.warning(f"  Error loading example {i}: {e}")
                continue

    logger.info(f"✅ Loaded {loaded_count} MuSiQue examples into smartmemoryapi")
    return loaded_count


async def check_smartmemory_health() -> bool:
    """Check if smartmemoryapi is running"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{SMARTMEMORY_URL}/health")
            if response.status_code == 200:
                data = response.json()
                logger.info(f"✅ SmartMemoryAPI is healthy: {data.get('service')} v{data.get('version')}")
                return True
            else:
                logger.error(f"❌ SmartMemoryAPI health check failed: {response.status_code}")
                return False
    except Exception as e:
        logger.error(f"❌ Cannot connect to SmartMemoryAPI at {SMARTMEMORY_URL}: {e}")
        return False


async def get_dataset_count() -> int:
    """Get current count of dataset memories"""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                f"{SMARTMEMORY_URL}/search",
                json={
                    "query": "",
                    "user_id": "datasets",
                    "limit": 1
                }
            )
            if response.status_code == 200:
                data = response.json()
                return len(data.get("memories", []))
    except:
        pass
    return 0


async def main():
    parser = argparse.ArgumentParser(description="Load HuggingFace datasets into SmartMemoryAPI")
    parser.add_argument(
        "--dataset",
        choices=["hotpotqa", "musique", "all"],
        default="hotpotqa",
        help="Dataset to load (default: hotpotqa)"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Number of examples to load per dataset (default: 100)"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8099",
        help="SmartMemoryAPI URL (default: http://localhost:8099)"
    )

    args = parser.parse_args()

    # Update global URL if specified
    global SMARTMEMORY_URL
    SMARTMEMORY_URL = args.url

    # Check health
    logger.info("Checking SmartMemoryAPI health...")
    if not await check_smartmemory_health():
        logger.error("SmartMemoryAPI is not available. Exiting.")
        return 1

    # Check current dataset count
    current_count = await get_dataset_count()
    logger.info(f"Current dataset memories in smartmemoryapi: {current_count}")

    # Load datasets
    total_loaded = 0

    if args.dataset in ["hotpotqa", "all"]:
        count = await load_hotpotqa(args.limit)
        total_loaded += count

    if args.dataset in ["musique", "all"]:
        count = await load_musique(args.limit if args.dataset == "musique" else args.limit // 2)
        total_loaded += count

    # Final count
    final_count = await get_dataset_count()
    logger.info(f"\n🎉 Complete! Loaded {total_loaded} new examples")
    logger.info(f"Total dataset memories: {current_count} → {final_count}")
    logger.info(f"\nTest with: Use dataset_rag to answer: 'example question'")

    return 0


if __name__ == "__main__":
    exit(asyncio.run(main()))
