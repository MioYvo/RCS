REPLACER = '^^^'


def convert_json_schema_to_son(schema: dict):
    for key in list(schema):
        if isinstance(schema[key], dict):
            schema[key] = convert_json_schema_to_son(schema[key])
        if key.startswith('$'):
            schema[f'{REPLACER}{key}'] = schema[key]
            schema.pop(key)
    return schema


def convert_son_to_json_schema(son: dict):
    for key in list(son):
        if isinstance(son[key], dict):
            son[key] = convert_son_to_json_schema(son[key])
        if key.startswith(REPLACER):
            son[key[len(REPLACER):]] = son[key]
            son.pop(key)
    return son
