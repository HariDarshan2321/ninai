"""Ninai desktop application: a native window control panel over the local vault.

The desktop app runs as the vault owner (the local operator) and therefore has
full read/write access to the vault, unlike an untrusted MCP client. It must
never be exposed over a network.
"""
