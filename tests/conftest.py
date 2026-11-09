"""Every test run gets a throwaway memory: tests never add runs, lessons or logged decisions to the hive's real
memory (logged decisions teach the hive new cells, team/cells/learn.py)."""
import os
import tempfile

os.environ["AGENT_TEAM_HOME"] = tempfile.mkdtemp(prefix="hive-test-memory-")
