"""Independently decode a practice task and evaluate it in event order for a cross-check."""
import configparser
import csv
import io
import json


def records(spec, data):
    if spec.form == 'queue':
        return data
    if spec.form == 'csv':
        rows = csv.DictReader(io.StringIO(data))
    elif spec.form == 'json':
        rows = json.loads(data)
    else:
        ini = configparser.ConfigParser()
        ini.read_string(data)
        rows = (ini[section] for section in ini.sections())
    return [(row['label'], int(row['value'])) for row in rows]


def streaming(spec, data):
    values, previous, runs, alerts = {}, {}, {}, []
    for label, value in records(spec, data):
        values.setdefault(label, 0)
        if spec.rule == 'rank' and value >= spec.threshold:
            values[label] += value
        elif spec.rule == 'wrap':
            values[label] += (value - previous.get(label, value)) % spec.modulus
        elif spec.rule == 'streak':
            runs[label] = runs.get(label, 0) + 1 if value >= spec.threshold else 0
            if runs[label] == spec.patience:
                alerts.append(label)
        previous[label] = value
    if spec.rule == 'last':
        return [k for k, value in previous.items() if value >= spec.threshold]
    if spec.rule == 'rank':
        return sorted(values, key=values.get, reverse=True)
    return alerts if spec.rule == 'streak' else values
