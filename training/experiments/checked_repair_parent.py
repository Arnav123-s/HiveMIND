"""Frozen G47 data cell function, extracted verbatim from the whole-hive-g47 observation."""


def exposure(points, ceiling, max_gap):
    if not points:
        return [0.0, 0]

    total_above = 0.0
    eligible_segments = 0

    for i in range(1, len(points)):
        prev_time, prev_reading = points[i - 1]
        curr_time, curr_reading = points[i]

        if prev_reading is None or curr_reading is None:
            continue

        if curr_time - prev_time > max_gap:
            continue

        start_time = prev_time
        start_reading = prev_reading
        end_time = curr_time
        end_reading = curr_reading

        if start_reading <= ceiling and end_reading > ceiling:
            eligible_segments += 1
            duration = end_time - start_time
            if start_reading == end_reading:
                total_above += duration
            else:
                delta = (end_reading - ceiling) / (end_reading - start_reading)
                total_above += delta * duration

    return [total_above, eligible_segments]
