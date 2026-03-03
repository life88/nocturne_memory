from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine
from sqlalchemy import inspect as sa_inspect

async def up(engine: AsyncEngine):
    """
    Version: v1.1.0 (from v1.0.4)
    Add graph-schema columns (node_uuid on memories, edge_id on paths).
    New tables 'nodes' and 'edges' are created by create_all before this runs.
    """
    def check_mem_col(connection):
        inspector = sa_inspect(connection)
        return "node_uuid" in [col["name"] for col in inspector.get_columns("memories")]
        
    def check_path_col(connection):
        inspector = sa_inspect(connection)
        return "edge_id" in [col["name"] for col in inspector.get_columns("paths")]

    async with engine.begin() as conn:
        has_mem_col = await conn.run_sync(check_mem_col)
        if not has_mem_col:
            await conn.execute(text("ALTER TABLE memories ADD COLUMN node_uuid VARCHAR(36) REFERENCES nodes(uuid)"))
            
        has_path_col = await conn.run_sync(check_path_col)
        if not has_path_col:
            await conn.execute(text("ALTER TABLE paths ADD COLUMN edge_id INTEGER REFERENCES edges(id)"))
