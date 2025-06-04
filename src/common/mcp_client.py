import os
import json
import asyncio
import logging
from typing import Dict, Any, List, Optional
import aiohttp
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MCPServerConfig:
    """Configuration for an MCP server"""
    name: str
    url: str
    timeout: int = 30

class MCPClient:
    """
    Client for communicating with MCP servers.
    Provides a unified interface for calling tools across multiple MCP servers.
    """
    
    def __init__(self):
        self.servers = self._load_server_configs()
        self.session: Optional[aiohttp.ClientSession] = None
        
    def _load_server_configs(self) -> Dict[str, MCPServerConfig]:
        """Load MCP server configurations from environment variables"""
        servers = {}
        
        # Map of server names to their environment variable names
        server_mappings = {
            'filesystem': 'MCP_FILESYSTEM_URL',
            'git': 'MCP_GIT_URL', 
            'fetch': 'MCP_FETCH_URL',
            'memory': 'MCP_MEMORY_URL',
            'sequentialthinking': 'MCP_SEQUENTIALTHINKING_URL',
            'time': 'MCP_TIME_URL',
            'context7': 'MCP_CONTEXT7_URL'
        }
        
        for server_name, env_var in server_mappings.items():
            url = os.getenv(env_var)
            if url:
                servers[server_name] = MCPServerConfig(
                    name=server_name,
                    url=url
                )
                logger.info(f"Configured MCP server: {server_name} at {url}")
        
        return servers
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Call a tool on a specific MCP server
        
        Args:
            server_name: Name of the MCP server (e.g., 'filesystem', 'git')
            tool_name: Name of the tool to call
            arguments: Arguments to pass to the tool
            
        Returns:
            Tool execution result
            
        Raises:
            ValueError: If server not configured
            aiohttp.ClientError: If request fails
        """
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' not configured")
            
        server = self.servers[server_name]
        
        if not self.session:
            raise RuntimeError("MCPClient not initialized. Use 'async with MCPClient() as client:'")
        
        # MCP tool call payload
        payload = {
            "jsonrpc": "2.0",
            "id": f"{server_name}_{tool_name}_{id(arguments)}",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        try:
            async with self.session.post(
                f"{server.url}/mcp",
                json=payload,
                timeout=server.timeout,
                headers={"Content-Type": "application/json"}
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                if "error" in result:
                    raise Exception(f"MCP tool error: {result['error']}")
                    
                logger.debug(f"MCP tool call successful: {server_name}.{tool_name}")
                return result.get("result", {})
                
        except asyncio.TimeoutError:
            logger.error(f"Timeout calling {server_name}.{tool_name}")
            raise
        except aiohttp.ClientError as e:
            logger.error(f"HTTP error calling {server_name}.{tool_name}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error calling {server_name}.{tool_name}: {e}")
            raise
    
    async def list_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """
        List available tools on a specific MCP server
        
        Args:
            server_name: Name of the MCP server
            
        Returns:
            List of available tools with their schemas
        """
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' not configured")
            
        server = self.servers[server_name]
        
        if not self.session:
            raise RuntimeError("MCPClient not initialized")
        
        payload = {
            "jsonrpc": "2.0",
            "id": f"list_tools_{server_name}",
            "method": "tools/list"
        }
        
        try:
            async with self.session.post(
                f"{server.url}/mcp",
                json=payload,
                timeout=server.timeout
            ) as response:
                response.raise_for_status()
                result = await response.json()
                
                if "error" in result:
                    raise Exception(f"MCP error: {result['error']}")
                    
                return result.get("result", {}).get("tools", [])
                
        except Exception as e:
            logger.error(f"Error listing tools for {server_name}: {e}")
            raise
    
    async def get_server_info(self, server_name: str) -> Dict[str, Any]:
        """Get server information and capabilities"""
        if server_name not in self.servers:
            raise ValueError(f"MCP server '{server_name}' not configured")
            
        server = self.servers[server_name]
        
        try:
            async with self.session.get(
                f"{server.url}/health",
                timeout=10
            ) as response:
                if response.status == 200:
                    return {
                        "name": server_name,
                        "url": server.url,
                        "status": "healthy",
                        "tools": await self.list_tools(server_name)
                    }
                else:
                    return {
                        "name": server_name,
                        "url": server.url,
                        "status": "unhealthy",
                        "error": f"HTTP {response.status}"
                    }
        except Exception as e:
            return {
                "name": server_name,
                "url": server.url,
                "status": "error",
                "error": str(e)
            }
    
    def get_configured_servers(self) -> List[str]:
        """Get list of configured server names"""
        return list(self.servers.keys())


# Convenience functions for common MCP operations
async def analyze_codebase(file_paths: List[str], language: str = None) -> Dict[str, Any]:
    """
    Analyze codebase structure using filesystem and git MCP servers
    """
    async with MCPClient() as client:
        # Use filesystem server to read files
        file_contents = {}
        for file_path in file_paths:
            try:
                result = await client.call_tool('filesystem', 'read_file', {
                    'path': file_path
                })
                file_contents[file_path] = result.get('content', '')
            except Exception as e:
                logger.warning(f"Could not read {file_path}: {e}")
        
        # Use git server to get repository info
        git_info = {}
        try:
            git_info = await client.call_tool('git', 'get_repository_info', {})
        except Exception as e:
            logger.warning(f"Could not get git info: {e}")
        
        return {
            'files': file_contents,
            'git_info': git_info,
            'total_files': len(file_contents),
            'languages_detected': [language] if language else []
        }

async def modify_file(file_path: str, content: str, create_backup: bool = True) -> Dict[str, Any]:
    """
    Modify a file using the filesystem MCP server
    """
    async with MCPClient() as client:
        if create_backup:
            # Create backup first
            try:
                await client.call_tool('filesystem', 'copy_file', {
                    'source': file_path,
                    'destination': f"{file_path}.backup"
                })
            except Exception as e:
                logger.warning(f"Could not create backup: {e}")
        
        # Write new content
        return await client.call_tool('filesystem', 'write_file', {
            'path': file_path,
            'content': content
        })

async def git_operations(operation: str, **kwargs) -> Dict[str, Any]:
    """
    Perform git operations using the git MCP server
    """
    async with MCPClient() as client:
        return await client.call_tool('git', operation, kwargs) 