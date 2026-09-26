import warnings


class GraphWorkbenchDeprecationWarning(DeprecationWarning):
    """Warning category for deprecated st-graph-workbench compatibility APIs."""


warnings.simplefilter("once", GraphWorkbenchDeprecationWarning)
