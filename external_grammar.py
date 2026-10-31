"""Validated bounded JSON grammars using the existing Choices mechanism."""
import json


class ConfigError(ValueError):
    pass


def validate_grammar(node, depth=0):
    if depth > 8 or not isinstance(node, dict):
        raise ConfigError('grammar exceeds depth 8 or contains a non-object node')
    kind = node.get('type')
    if kind == 'enum':
        values = node.get('values')
        if not isinstance(values, list) or not 1 <= len(values) <= 256:
            raise ConfigError('enum values must have length 1..256')
        try:
            json.dumps(values, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise ConfigError('enum values must be finite JSON') from error
    elif kind == 'int':
        low, high = node.get('min'), node.get('max')
        if type(low) is not int or type(high) is not int or not 0 <= high-low <= 255:
            raise ConfigError('int bounds must be integers with span 0..255')
    elif kind == 'object':
        fields = node.get('fields')
        if not isinstance(fields, dict) or not 1 <= len(fields) <= 32:
            raise ConfigError('object fields must have length 1..32')
        for name, child in fields.items():
            if not isinstance(name, str) or not name:
                raise ConfigError('field names must be nonempty strings')
            validate_grammar(child, depth+1)
    elif kind == 'array':
        low, high = node.get('min_length'), node.get('max_length')
        if type(low) is not int or type(high) is not int or not 0 <= low <= high <= 32:
            raise ConfigError('array length must be bounded within 0..32')
        validate_grammar(node.get('items'), depth+1)
    else:
        raise ConfigError(f'unknown grammar type: {kind}')


def generate(node, source):
    kind = node['type']
    if kind == 'enum':
        return source.choose(node['values'])
    if kind == 'int':
        return source.choose(tuple(range(node['min'], node['max'] + 1)))
    if kind == 'object':
        return {key: generate(child, source) for key, child in node['fields'].items()}
    length = source.choose(tuple(range(node['min_length'], node['max_length'] + 1)))
    return [generate(node['items'], source) for _ in range(length)]
