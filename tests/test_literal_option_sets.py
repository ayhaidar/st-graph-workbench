from st_graph_workbench.component import commands, component
from st_graph_workbench.component._typing import literal_choices


def test_component_validation_sets_match_public_literal_aliases():
    assert component._NODE_ACTIONS == literal_choices(component.NodeAction)
    assert component._CRUD_ACTIONS == literal_choices(component.CrudAction)
    assert component._EDIT_ACTIONS == literal_choices(component.EditAction)
    assert component._VIEWPORT_ACTIONS == literal_choices(component.ViewportAction)
    assert component._SELECTION_MODES == literal_choices(component.SelectionMode)
    assert component._ANALYSIS_ACTIONS == literal_choices(component.AnalysisAction)
    assert component._PERFORMANCE_PROFILES == literal_choices(
        component.PerformanceProfile
    )
    assert component._ELEMENTS_SYNC_MODES == literal_choices(component.ElementsSync)


def test_graph_command_validation_sets_match_literal_aliases():
    graph_command_operations = literal_choices(commands.GraphCommandOperation)
    viewport_command_operations = literal_choices(commands.ViewportCommandOperation)

    assert commands._GRAPH_COMMAND_OPERATIONS == graph_command_operations
    assert viewport_command_operations <= graph_command_operations
