"""
Shared in-memory state for actuator decisions and manual overrides.
Used by both the control loop and API endpoints.
"""

# Tracks the last known state of each actuator
last_decision = {
    "fan": "off",
    "light": "off",
    "pump": "off",
}

# Tracks manual locks on actuators: { "fan": ("on", expiry_timestamp), ... }
manual_lock = {}

def get_last_decision() -> dict:
    """
    Returns a copy of the current actuator state dictionary.
    """
    return last_decision.copy()
