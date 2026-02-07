"""
Feature flags for the agentic fitness app.

Set these to True/False to enable or disable graph nodes.
When False, the corresponding node is not added to the graph and is skipped in the flow.
"""

# When True, the decay node runs after supervisor (time-based fatigue decay).
# When False, supervisor connects directly to the next step (history_analysis or routing).
ENABLE_DECAY = False

# When True, the history_analysis node runs (applies fatigue from previous workout).
# When False, decay (or supervisor) connects directly to worker routing.
ENABLE_HISTORY_ANALYZER = False
