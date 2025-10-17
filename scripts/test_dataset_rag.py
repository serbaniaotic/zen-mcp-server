#!/usr/bin/env python3
"""
Test dataset_rag tool locally or via HTTP bridge

Usage:
    # Test locally
    python scripts/test_dataset_rag.py --local

    # Test via HTTP bridge
    python scripts/test_dataset_rag.py --remote --url http://localhost:8766
"""

import asyncio
import argparse
import sys
import os
import logging

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import httpx

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


async def test_local():
    """Test dataset_rag tool locally"""
    from tools.dataset_rag import DatasetRAGTool

    logger.info("Testing dataset_rag tool locally...")

    tool = DatasetRAGTool()

    # Test query
    query = "What are examples of multi-hop reasoning?"

    logger.info(f"Query: {query}")
    logger.info("Executing tool...")

    try:
        result = await tool.execute({
            "query": query,
            "dataset": "all",
            "use_graph_reasoning": True,
            "max_hops": 3
        })

        logger.info(f"\n{'='*60}")
        logger.info("RESULT:")
        logger.info(f"{'='*60}")
        print(result)
        logger.info(f"{'='*60}\n")

        return True

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def test_remote(url: str):
    """Test dataset_rag via HTTP bridge"""
    logger.info(f"Testing dataset_rag via HTTP bridge at {url}...")

    # Test query
    query = "What are examples of multi-hop reasoning?"

    logger.info(f"Query: {query}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{url}/chat",
                json={
                    "transcript": f"Use dataset_rag to answer: {query}",
                    "tool_override": "dataset_rag",
                    "auto_route": False
                }
            )

            if response.status_code == 200:
                data = response.json()

                logger.info(f"\n{'='*60}")
                logger.info("RESULT:")
                logger.info(f"{'='*60}")
                logger.info(f"Success: {data.get('success')}")
                logger.info(f"Tool used: {data.get('tool_used')}")
                logger.info(f"\nResponse:\n{data.get('response')}")
                logger.info(f"{'='*60}\n")

                return data.get('success', False)
            else:
                logger.error(f"❌ HTTP error: {response.status_code}")
                logger.error(response.text)
                return False

    except Exception as e:
        logger.error(f"❌ Test failed: {e}", exc_info=True)
        return False


async def main():
    parser = argparse.ArgumentParser(description="Test dataset_rag tool")
    parser.add_argument(
        "--local",
        action="store_true",
        help="Test locally (default)"
    )
    parser.add_argument(
        "--remote",
        action="store_true",
        help="Test via HTTP bridge"
    )
    parser.add_argument(
        "--url",
        default="http://localhost:8766",
        help="HTTP bridge URL (default: http://localhost:8766)"
    )

    args = parser.parse_args()

    # Default to local if neither specified
    if not args.local and not args.remote:
        args.local = True

    success = False

    if args.local:
        success = await test_local()

    if args.remote:
        success = await test_remote(args.url)

    if success:
        logger.info("✅ Test passed!")
        return 0
    else:
        logger.error("❌ Test failed!")
        return 1


if __name__ == "__main__":
    exit(asyncio.run(main()))
