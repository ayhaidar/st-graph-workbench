# Managed expansion API

## On this page

- [Controller](#controller)
- [Requests and providers](#requests-and-providers)
- [Configuration and operations](#configuration-and-operations)

Managed expansion keeps application-owned source data separate from cached
records and the displayed graph. Start with the [branch guide](../guides/expansion-visibility.md).

## Controller

::: st_graph_workbench.component.expansion.ExpansionController

## Requests and providers

::: st_graph_workbench.component.expansion.ExpansionRequest

::: st_graph_workbench.component.expansion.ExpansionResponse

::: st_graph_workbench.component.expansion.ExpansionProvider

::: st_graph_workbench.component.expansion_provider.InMemoryExpansionProvider

## Configuration and operations

::: st_graph_workbench.component.expansion.ExpansionConfig

::: st_graph_workbench.component.expansion.ExpansionOperation

Events use `action="expansion"`. The operation is one of `expand`, `load_more`,
`collapse`, `collapse_all`, `expand_all`, `protect`, `unprotect`, `cancel`,
`retry`, `reveal`, `search`, `analyze`, or `continue`.
The exploration dialog is browser-local; `continue` schedules a single bulk batch.
Applications normally pass returned events to `controller.handle_event(event, provider)`.
