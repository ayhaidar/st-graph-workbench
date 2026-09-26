# Multiple graph instances

## On this page

- [Use unique keys](#use-unique-keys)
- [Keep state separate](#keep-state-separate)
- [Update options safely](#update-options-safely)
- [Complete pattern](#complete-pattern)

## Use unique keys

Every graph on a page needs a stable and unique `key`. The component encodes
the key into a Streamlit-safe internal identifier without collapsing similar
values such as `case__left` and `case--left`.

## Keep state separate

Use separate element dictionaries, command queues, event timestamps, and saved
viewports for each graph. Do not route both `on_change` callbacks through a
single unqualified session-state key.

## Update options safely

Selection modes, zoom bounds, heights, and custom event listeners can update on
one live graph without changing the other. Initialization-only changes should
remount only the intended graph by changing that graph's key.

## Complete pattern

```python
--8<-- "docs/snippets/multiple_instances.py"
```

This is useful for comparing two cases, a full network and focused subgraph, or
current and historical observations. Each returned dictionary remains tied to
its own component instance.

## Conclusion

Component keys are part of application state design. Name them by durable view
identity, not by transient layout or selection values.
