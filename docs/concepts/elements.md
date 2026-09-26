# Graph elements

## On this page

- [Top-level contract](#top-level-contract)
- [Node records](#node-records)
- [Edge records](#edge-records)
- [Identifiers](#identifiers)
- [Compound nodes](#compound-nodes)
- [Expansion metadata](#expansion-metadata)
- [Validation](#validation)

## Top-level contract

The component accepts a dictionary with `nodes` and `edges` lists:

```python
elements = {
    "nodes": [{"data": {"id": "ABC123", "label": "VEHICLE"}}],
    "edges": [],
}
```

Unknown data fields are preserved and remain available to selectors, search,
event payloads, exports, and application logic.

## Node records

`data.id` is required. `data.label` is required in strict validation and is
used by `NodeStyle`. `data.name` is a conventional display field rather than a
required key.

```python
{
    "data": {
        "id": "camera-7",
        "label": "LOCATION",
        "name": "Harbour camera 7",
        "risk": 8,
        "source_system": "ANPR",
    },
    "position": {"x": 420, "y": 180},
}
```

`position` is useful with the `preset` layout. Cytoscape also understands
element-level fields such as `selected`, `locked`, and `grabbable`.

## Edge records

Edges require unique `data.id`, `data.source`, and `data.target` values. Both
endpoints must refer to existing nodes.

```python
{
    "data": {
        "id": "ABC123-camera-7",
        "label": "SEEN_AT",
        "source": "ABC123",
        "target": "camera-7",
        "confidence": 0.96,
    }
}
```

## Identifiers

Public helpers accept a non-empty scalar string, finite number, or boolean as an ID
and normalize it to text. Lists, dictionaries, byte strings, `NaN`, infinity,
empty strings, and `None` are not valid individual IDs. Treat IDs as durable
application identifiers, not row positions or display labels.

## Compound nodes

Set `data.parent` on a child node to the ID of another node:

```python
{"data": {"id": "case-42", "label": "CASE", "name": "Case 42"}}
{"data": {"id": "ABC123", "label": "VEHICLE", "parent": "case-42"}}
```

Parents must exist, cannot refer to themselves, and cannot create cycles.

## Expansion metadata

Only nodes with genuine related records should carry `data.expansion`:

```python
{
    "state": "collapsed",
    "next_count": 2,
    "total_count": 5,
    "depth": 1,
}
```

- `state` is `collapsed` or `expanded`.
- `next_count` is the number of records added by the next expansion.
- `collapse_count` is the number removed by collapse.
- `total_count` is the exact remaining or affected total shown in details.
- Counts are finite non-negative numbers. A node with no expansion must omit
  the object instead of displaying a misleading `+0` or `+2` badge.

## Validation

```python
from st_graph_workbench import ElementValidationError, validate_elements

try:
    validate_elements(elements)
except ElementValidationError as error:
    print(error)
```

Strict validation checks collection shape, required fields, unique IDs, edge
references, parent references and cycles, and expansion metadata. The
`graph_workbench(..., validate=True)` default invokes it before rendering.

## Conclusion

Validate at ingestion boundaries as well as before rendering. This turns blank
or partially rendered graphs into actionable Python errors close to the source.
