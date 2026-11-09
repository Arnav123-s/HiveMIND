"""Every test run gets a throwaway memory: tests never add runs, lessons or logged decisions to the hive's real
memory (logged decisions teach the hive new cells, team/cells/learn.py)."""
import os
import tempfile

os.environ["AGENT_TEAM_HOME"] = tempfile.mkdtemp(prefix="hive-test-memory-")
os.environ["AGENT_TEAM_DISK_STOP_GB"] = "0"  # the test machine's free disk must not refuse the tests' stand-in jobs
os.environ["AGENT_TEAM_CONVERSE"] = "0"  # old tests send every message as a job; conversation tests turn it on
