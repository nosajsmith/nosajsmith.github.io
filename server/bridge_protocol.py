"""
Bridge protocol constants (locked).
"""

PROTOCOL_VERSION = "1.0"

# Envelope keys
K_ID = "id"
K_CMD = "cmd"
K_ARGS = "args"

# Response keys
K_STATUS = "status"   # "ok" | "error"
K_DATA = "data"
K_ERROR = "error"

# Error shape
# error = {"code": "...", "message": "...", "details": {...}}

# Commands
CMD_PING = "ping"
CMD_CAPABILITIES = "capabilities"
CMD_GET_STATE = "get_state"
CMD_STATUS = "status"
CMD_LIST_SCENARIOS = "list_scenarios"
CMD_LOAD_SCENARIO = "load_scenario"
CMD_SAVE_SCENARIO = "save_scenario"
