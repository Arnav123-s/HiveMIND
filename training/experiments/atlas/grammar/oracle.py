"""Strict schema validity and separate unambiguous payload accuracy. No model dependency."""
import json
import re

def _unique(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError('duplicate key')
        out[k] = v
    return out

def _valid(value, definition):
    kind = definition['type']
    if kind == 'int':
        return type(value) is int
    if kind == 'bool':
        return type(value) is bool
    if kind == 'enum':
        return type(value) is str and value in definition['options']
    raise ValueError('unknown field type')

def _parse(row, text):
    kind, schema = row['format'], row['schema']
    if kind == 'enum':
        if text not in schema['options']:
            raise ValueError('unlisted label')
        return text
    if kind == 'csv':
        # A single unquoted row of typed scalars; whitespace around cells is harmless.
        if '\n' in text or '\r' in text:
            raise ValueError('too many CSV rows')
        cells = [s.strip() for s in text.split(',')]
        if len(cells) != len(schema['fields']):
            raise ValueError('wrong CSV width')
        out = []
        for cell, spec in zip(cells, schema['fields']):
            if spec['type'] == 'int':
                if not re.fullmatch(r'-?(?:0|[1-9][0-9]*)', cell):
                    raise ValueError('expected integer')
                cell = int(cell)
            if not _valid(cell, spec):
                raise ValueError('wrong CSV type')
            out.append(cell)
        return out
    value = json.loads(text, object_pairs_hook=_unique)
    if kind == 'array':
        if not isinstance(value, list) or any(type(v) is not int for v in value):
            raise ValueError('expected integer array')
        return value
    if kind == 'object':
        fields = schema['fields']
        if type(value) is not dict or set(value) != {f['name'] for f in fields}:
            raise ValueError('wrong keys')
        if not all(_valid(value[f['name']], f) for f in fields):
            raise ValueError('wrong field value')
        return value
    raise ValueError('unknown format')

def grade(row, expected, raw_text):
    text = raw_text.strip()
    try:
        parsed = _parse(row, text)
        return dict(format_ok=True, content_ok=(parsed == expected), parsed=parsed)
    except (ValueError, TypeError):
        pass
    # A complete, single fenced block or conventional answer prefix may retain the content.
    fence = re.fullmatch(r'```(?:json|csv|text)?\s*\n(.*?)\n```', text, flags=re.S | re.I)
    candidate = fence[1].strip() if fence else re.sub(r'^(?:answer|result|output)\s*:\s*', '', text, count=1, flags=re.I)
    try:
        parsed = _parse(row, candidate)
    except (ValueError, TypeError):
        parsed = None
    return dict(format_ok=False, content_ok=(parsed is not None and parsed == expected), parsed=parsed)
