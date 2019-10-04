def get_nested_field(field, dict_to_travel):
    splited_params = field.split(".", 1)
    field_value = dict_to_travel.get(splited_params[0], {})
    if len(splited_params) > 1:
        field_value = get_nested_field(
            splited_params[1],
            field_value)
    return field_value
