# Styling and icons

## On this page

- [Style layers](#style-layers)
- [NodeStyle](#nodestyle)
- [EdgeStyle](#edgestyle)
- [StyleRule](#stylerule)
- [Packaged icons](#packaged-icons)
- [Readable encodings](#readable-encodings)

## Style layers

`NodeStyle` and `EdgeStyle` cover common label-based styling. `StyleRule`
accepts a Cytoscape selector and raw style properties for state or
property-driven rules. Later rules can override earlier matching properties.

## NodeStyle

```python
node_styles = [
    NodeStyle(
        "VEHICLE",
        color="#2A629A",
        caption="name",
        icon="directions_car",
        size=36,
        shape="ellipse",
        border_color="#17324D",
        border_width=2,
        opacity=1,
        label_position="bottom",
        text_size=12,
    )
]
```

The first argument matches `node.data.label`. `caption` names the data field
shown as text. Valid helper label positions are `top`, `center`, and `bottom`.
Use `raw_style` for Cytoscape properties not exposed as named arguments.

## EdgeStyle

```python
edge_styles = [
    EdgeStyle(
        "SEEN_AT",
        color="#2D936C",
        caption="label",
        directed=True,
        curve_style="bezier",
        width=3,
        line_style="dashed",
        opacity=0.9,
        target_arrow="triangle",
    )
]
```

`directed=True` supplies a target arrow unless one is explicitly configured.
Line style, curve style, width, arrows, opacity, captions, and raw Cytoscape
properties can communicate relationship type and confidence.

## StyleRule

```python
StyleRule(
    "node[risk >= 8]",
    {
        "border-color": "#D72638",
        "border-width": 5,
        "background-color": "#FFF4E6",
    },
)
```

Selectors can target data values, selected state, parent nodes, or graph
classes. Keep business data in `data`; use selectors to turn that data into a
visual encoding.

## Packaged icons

Icon names are Material Symbols-style SVG assets shipped inside the wheel.
Use the exact supported name in `NodeStyle(icon=...)`. Browse the searchable
catalog in the local Streamlit examples app at `/supported_icons`.

An unsupported name falls back to the ordinary node body; it is better to
validate style choices against the catalog during development.

## Readable encodings

- Use color primarily for entity type, not every individual node.
- Use shape or icon as a second channel where color vision may vary.
- Keep edge direction and relationship labels visible when direction matters.
- Reserve strong borders for selected, high-risk, or exceptional records.
- Test dense graphs at low zoom because performance profiles may hide labels.

## Conclusion

Start with helper styles and add selector rules only where data-driven emphasis
improves interpretation. See the generated [styling reference](../reference/styles.md)
for every argument.
