"""
Database configuration for Zen MCP Server
Provides connection details for all databases in the hybrid architecture.
"""

import os
from typing import Dict, Any


class DatabaseConfig:
    """Configuration for all databases used by Zen MCP Server"""
    
    # Postgres configuration (Task Queue, Source of Truth)
    POSTGRES_CONFIG = {
        "host": os.getenv("POSTGRES_HOST", "localhost"),
        "port": int(os.getenv("POSTGRES_PORT", "5434")),
        "database": os.getenv("POSTGRES_DB", "zendb"),
        "user": os.getenv("POSTGRES_USER", "zen"),
        "password": os.getenv("POSTGRES_PASSWORD", "zenpass"),
    }
    
    # DuckDB configuration (Analytics)
    DUCKDB_PATH = os.getenv("DUCKDB_PATH", str(os.path.expanduser("~/.zen-mcp/analytics.duckdb")))
    
    # Pinecone configuration (Semantic Intelligence)
    PINECONE_CONFIG = {
        "api_key": os.getenv("PINECONE_API_KEY", ""),
        "environment": os.getenv("PINECONE_ENVIRONMENT", ""),
        "index_name": os.getenv("PINECONE_INDEX", "zen-mcp"),
    }
    
    # Memgraph configuration (Relationship Mapping)
    MEMGRAPH_CONFIG = {
        "uri": os.getenv("MEMGRAPH_URI", "bolt://localhost:7687"),
        "user": os.getenv("MEMGRAPH_USER", ""),
        "password": os.getenv("MEMGRAPH_PASSWORD", ""),
    }
    
    @classmethod
    def get_postgres_connection_string(cls) -> str:
        """Get Postgres connection string"""
        cfg = cls.POSTGRES_CONFIG
        return f"postgresql://{cfg['user']}:{cfg['password']}@{cfg['host']}:{cfg['port']}/{cfg['database']}"
    
    @classmethod
    def get_postgres_dsn(cls) -> Dict[str, Any]:
        """Get Postgres DSN for psycopg2"""
        return cls.POSTGRES_CONFIG.copy()
    
    @classmethod
    def get_duckdb_path(cls) -> str:
        """Get DuckDB database file path"""
        return cls.DUCKDB_PATH
    
    @classmethod
    def get_memgraph_uri(cls) -> str:
        """Get Memgraph connection URI"""
        return cls.MEMGRAPH_CONFIG["uri"]
    
    @classmethod
    def validate_postgres(cls) -> bool:
        """Validate Postgres configuration"""
        import psycopg2
        try:
            conn = psycopg2.connect(**cls.get_postgres_dsn())
            conn.close()
            return True
        except Exception:
            return False
    
    @classmethod
    def validate_duckdb(cls) -> bool:
        """Validate DuckDB configuration"""
        import duckdb
        try:
            conn = duckdb.connect(cls.get_duckdb_path())
            conn.close()
            return True
        except Exception:
            return False
    
    @classmethod
    def print_config_summary(cls):
        """Print configuration summary"""
        print("=" * 60)
        print("Zen MCP Server - Database Configuration")
        print("=" * 60)
        print("\n1. Postgres (Task Queue, Source of Truth)")
        print(f"   Host: {cls.POSTGRES_CONFIG['host']}:{cls.POSTGRES_CONFIG['port']}")
        print(f"   Database: {cls.POSTGRES_CONFIG['database']}")
        print(f"   User: {cls.POSTGRES_CONFIG['user']}")
        print(f"   Status: {'✅ Valid' if cls.validate_postgres() else '❌ Invalid'}")
        
        print("\n2. DuckDB (Analytics Engine)")
        print(f"   Path: {cls.DUCKDB_PATH}")
        print(f"   Status: {'✅ Valid' if cls.validate_duckdb() else '❌ Invalid'}")
        
        print("\n3. Pinecone (Semantic Intelligence)")
        print(f"   Index: {cls.PINECONE_CONFIG['index_name']}")
        print(f"   Environment: {cls.PINECONE_CONFIG['environment'] or 'Not configured'}")
        
        print("\n4. Memgraph (Relationship Mapping)")
        print(f"   URI: {cls.MEMGRAPH_CONFIG['uri']}")
        
        print("=" * 60)


if __name__ == "__main__":
    DatabaseConfig.print_config_summary()

