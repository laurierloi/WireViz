# Objective

This file should track the various tasks currently in the queue for wireviz.
Some task might be far off/ not being worked on.
Yet having them here allows for a proper overview of the program's state.

# Naming convention

Complying with @laurierloi knowledge system:

CreationDate(YYMMDD);Github;{Task,Bug,Doc};Wireviz;Count_description

ex:
230328GTW1_try_to_use_pupeteer


# Tasks List

List of tasks according to system's concept.

Normally the tasks are sorted from most important to less important.
That ordering is somewhat arbitrary


## Documentation

- 230327GTW3_create_an_architecture_of_wireviz
- 230329GTW2_list_features_of_perfect_harness_diagram


## Tooling

- 230407GTW1_use_pydantic_basemodel_instead_of_dataclasses
- 230328GTW1_try_to_use_pupeteer
- 230727GTW1_setup_ruff_pre_commit


## Outputs

- 230329GTW2_bom_class_generate_excel_see_MR


## Views

- 230911GTW1_create_a_view_with_only_connection_table
- 230329GTW1_support_splitting_SVG_in_two
- 230717GTW1_support_dual_color_in_wire_see_ex10
- 230525GTW1_bom_on_separate_page_by_config
- 230327GTW1_create/include_egse_template
- 230329GTW1_create_low_level_view_as_only_pin_table
- 230329GTW2_create_high_level_view_as_only_connector
- 230329GTW3_support_symbols/icons
- 230414GTW1_titlepage_add_reference_to_documents
- 230330GTW1_support_light_dark_mode
- 230330GTW3_splice_option_for_start/end_of_harness
- 230330GTW5_cable_displayed_differently_according_to_layer


## Configuration

- 230331GTW1_central_shared_configuration_file_for_all_wireviz
- 230629GTW2_support_default_in_connection_to_do_a_pin_by_pin_match_directly
- 230330GTW2_template_styles_fully_configured_using_external_configuration


## Data Structure

- 230404GTW1_networkx_all_familly_info_within_a_graph
- 230531GTW1_use_BomContent_class_in_xsc_harness_and_for_shared_bom
- 230329GTW4_BOM_class_has_unique_id_per_part_from_instantiation
- 230629GTW1_use_notes_class_within_components
- 230327GTW1_try_networkx_to_represent_harness_connections
- 230327GTW2_try_networkx_to_represent_harnesses_connections
- 230327GTW4_part_independently_defined
- 230327GTW5_connector_from_a_part_library; depends:230327GTW4
- 230327GTW6_cable_from_a_part_library; depends:230327GTW4
- 230330GTW4_cable_are_recursive_aka_a_group_of_cable_or_wire
- 230330GTW6_outer_cable_is_just_a_bundle_of_bundle/cable/wire



# Extended descriptions

Provided optionally per task, extended descriptions refer to the tasks UID
