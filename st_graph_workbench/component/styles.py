import warnings
from typing import Optional, Dict, Any, Literal

from st_graph_workbench.component._warnings import GraphWorkbenchDeprecationWarning


class NodeStyle:
    """Configure a label-based Cytoscape node style.

    The style matches nodes whose ``data.label`` equals ``label``. Named
    arguments cover common visual properties; ``raw_style`` provides access to
    additional Cytoscape style properties.
    """

    def __init__(
        self,
        label: str,
        color: Optional[str] = None,
        caption: Optional[str] = None,
        icon: Optional[str] = None,
        size: Optional[float] = None,
        shape: Optional[str] = None,
        border_color: Optional[str] = None,
        border_width: Optional[float] = None,
        opacity: Optional[float] = None,
        label_position: Optional[Literal["top", "center", "bottom"]] = None,
        text_size: Optional[float] = None,
        raw_style: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Define a custom style of a node in the graph based on label.

        Parameters
        ----------
        label : str
            The label of the node. This label is used to identify the group or
            category of the node.
        color : Optional[str]
            Specifies the background color of the node. If not provided, the
            default node color "#0a0a0a" will be used.
        caption : Optional[str]
            Name of the node's attribute to use as caption/label. If not provided,
            no caption will be shown.
        icon: Optional[str]
            Node icon name from the bundled Material Symbols-style SVG assets
            (e.g. 'person') or a URL (e.g. url('...')). A list of supported
            icons is available in `st_graph_workbench.component.icons`.
        size: Optional[float]
            Node width and height in Cytoscape units.
        shape: Optional[str]
            Cytoscape node shape, such as 'ellipse', 'round-rectangle', or
            'diamond'.
        border_color: Optional[str]
            Node border color.
        border_width: Optional[float]
            Node border width in Cytoscape units.
        opacity: Optional[float]
            Node opacity from 0 to 1.
        label_position: Optional[Literal['top', 'center', 'bottom']]
            Vertical label placement relative to the node.
        text_size: Optional[float]
            Node label font size in Cytoscape units.
        raw_style: Optional[dict]
            Advanced Cytoscape style properties merged after the simple Python
            fields. Use this when Cytoscape supports a style that this wrapper
            does not name directly.

        Example
        -------
        >>> node_style = NodeStyle(label="Person", color="#345eeb", caption="name")
        """
        self.label = label
        self.color = color
        self.caption = caption
        self.icon = icon
        self.size = size
        self.shape = shape
        self.border_color = border_color
        self.border_width = border_width
        self.opacity = opacity
        self.label_position = label_position
        self.text_size = text_size
        self.raw_style = raw_style or {}

    def dump(self) -> Dict[str, Any]:
        """Return the style as a JSON-ready Cytoscape selector rule."""

        selector = f"node[label='{self.label}']"
        style: Dict[str, Any] = {}

        if self.color:
            style["background-color"] = self.color
        if self.caption:
            style["label"] = f"data({self.caption})"
        if self.icon:
            icon = self.icon
            if not icon.startswith("url") and not icon.endswith(".svg"):
                icon = f"./icons/{icon.lower()}.svg"
            style["background-image"] = icon
        if self.size is not None:
            style["width"] = self.size
            style["height"] = self.size
        if self.shape:
            style["shape"] = self.shape
        if self.border_color:
            style["border-color"] = self.border_color
        if self.border_width is not None:
            style["border-width"] = self.border_width
        if self.opacity is not None:
            style["opacity"] = self.opacity
        if self.label_position:
            style["text-valign"] = self.label_position
        if self.text_size is not None:
            style["font-size"] = self.text_size
        style.update(self.raw_style)

        return {
            "selector": selector,
            "style": style,
        }


class EdgeStyle:
    """Configure a label-based Cytoscape edge style.

    The style matches edges whose ``data.label`` equals ``label`` and can
    describe captions, direction, line appearance, arrows, and raw Cytoscape
    properties.
    """

    def __init__(
        self,
        label: str,
        color: Optional[str] = None,
        caption: Optional[str] = None,
        labeled: Optional[bool] = None,  # deprecated
        directed: bool = False,
        curve_style: Optional[str] = None,
        width: Optional[float] = None,
        line_style: Optional[str] = None,
        opacity: Optional[float] = None,
        source_arrow: Optional[str] = None,
        target_arrow: Optional[str] = None,
        raw_style: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Define a custom style of an edge in the graph based on label.

        Parameters
        ----------
        label : str
            The label of the edge. This label is used to identify the group or
            category of the edge.
        color : Optional[str]
            Specifies the color of the edge line.
        caption : Optional[str], default None
            Name of the edge's attribute to use as caption/label. If not provided,
            no caption will be shown.
        labeled : bool, default False (deprecated)
            Compatibility parameter retained for older examples. Use `caption`
            instead to specify edge caption/label. If `labeled` is set to True
            and `caption` is not provided, default caption 'label' will be used.
        directed : bool, default False
            Indicates whether the edge is directed. If True, the edge will be
            rendered with an arrow pointing from the source to target. Default
            is False. Note: Arrows will not be displayed if `curve_style`
            is set to "haystack".
        curve_style: Optional[str]
            Specifies the edge curving method to use. By default, it is set to
            "bezier", which is suitable for multigraphs. For large, simple graphs,
            consider using "haystack" for better performance. For more options
            and detailed information, visit: https://js.cytoscape.org/#style/edge-line
        width: Optional[float]
            Edge line width in Cytoscape units.
        line_style: Optional[str]
            Edge line style, such as 'solid', 'dashed', or 'dotted'.
        opacity: Optional[float]
            Edge opacity from 0 to 1.
        source_arrow: Optional[str]
            Cytoscape source arrow shape.
        target_arrow: Optional[str]
            Cytoscape target arrow shape. This overrides the default triangle
            used by `directed=True`.
        raw_style: Optional[dict]
            Advanced Cytoscape style properties merged after the simple Python
            fields.

        Example
        -------
        >>> edge_style = EdgeStyle(label="FOLLOWS", color="#345eeb")
        """
        self.label = label
        self.color = color
        self.caption = caption
        self.directed = directed
        self.curve_style = curve_style
        self.width = width
        self.line_style = line_style
        self.opacity = opacity
        self.source_arrow = source_arrow
        self.target_arrow = target_arrow
        self.raw_style = raw_style or {}

        if labeled is not None:
            warnings.warn(
                "Parameter `labeled` is deprecated. Please use the `caption` "
                "parameter instead.",
                GraphWorkbenchDeprecationWarning,
            )
        if labeled and not caption:
            self.caption = "label"

    def dump(self) -> Dict[str, Any]:
        """Return the style as a JSON-ready Cytoscape selector rule."""

        selector = f"edge[label='{self.label}']"
        style: Dict[str, Any] = {}

        if self.color:
            style["line-color"] = self.color
            style["background-color"] = self.color
            style["text-background-color"] = self.color
            style["target-arrow-color"] = self.color
        if self.caption:
            style["label"] = f"data({self.caption})"
        if self.directed:
            style["target-arrow-shape"] = "triangle"
        if self.curve_style:
            style["curve-style"] = self.curve_style
        if self.width is not None:
            style["width"] = self.width
        if self.line_style:
            style["line-style"] = self.line_style
        if self.opacity is not None:
            style["opacity"] = self.opacity
        if self.source_arrow:
            style["source-arrow-shape"] = self.source_arrow
        if self.target_arrow:
            style["target-arrow-shape"] = self.target_arrow
        style.update(self.raw_style)

        return {
            "selector": selector,
            "style": style,
        }


class StyleRule:
    """Configure an advanced Cytoscape selector and style dictionary."""

    def __init__(self, selector: str, style: Dict[str, Any]) -> None:
        """
        Define an advanced Cytoscape stylesheet rule.

        Use this escape hatch when `NodeStyle` or `EdgeStyle` do not expose a
        specific Cytoscape style property directly.
        """
        self.selector = selector
        self.style = style

    def dump(self) -> Dict[str, Any]:
        """Return a copy-ready Cytoscape selector/style dictionary."""

        return {
            "selector": self.selector,
            "style": self.style,
        }
