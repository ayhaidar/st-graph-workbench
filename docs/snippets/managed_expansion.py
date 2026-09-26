"""Run from the checkout: uv run python -m docs.snippets.managed_expansion."""

from examples.expansion_data import expansion_source, expansion_start
from st_graph_workbench import (
    ExpansionController,
    InMemoryExpansionProvider,
    records_to_dataframe,
)

source = expansion_source()
provider = InMemoryExpansionProvider(source)
controller = ExpansionController(expansion_start(), source_version="2026-01")

# Load the two locations, then their independent connections.
for node_id in ("ABC123", "location-1", "location-2", "camera-1"):
    controller.expand(node_id, provider)

# Location 1 and the vehicle remain. The shared report is retained by Location 2.
controller.collapse(["location-1"])
print(records_to_dataframe(controller.view()))
print(records_to_dataframe(controller.changes))

# Reopen from the cache, including the previously opened camera branch.
controller.expand("location-1", provider)
snapshot = controller.snapshot()
restored = ExpansionController.restore(snapshot, source_version="2026-01")
assert restored.view() == controller.view()
assert len(source["nodes"]) == 12  # Collapse never edited the source.
