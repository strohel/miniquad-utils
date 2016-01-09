#!/usr/bin/env python3

from collections import defaultdict
import csv
from glob import iglob
import json
import logging
import os

import numpy as np
import matplotlib.pyplot as plt


def col(colindex):
    if colindex is None:
        return '?'
    return chr(ord('A') + colindex)

class MeasurementIndexes:
    def __init__(self, U=None, I=None, thrust=None, rpm=None):
        self.U = U
        self.I = I
        self.thrust = thrust
        self.rpm = rpm

    def __str__(self):
        return "MeasurementIndexes(U={}, I={}, thrust={}, rpm={})".format(col(self.U), col(self.I),
                                                                          col(self.thrust), col(self.rpm))

    __repr__ = __str__

    def is_complete(self):
        return self.U is not None and self.I is not None \
               and self.thrust is not None and self.rpm is not None

class RowIndexes:
    def __init__(self, battery=None, prop=None, measurements=[]):
        self.battery = battery
        self.prop = prop
        self.measurements = measurements

    def __str__(self):
        return "RowIndexes(battery={}, prop={}, measurements={})".format(col(self.battery), col(self.prop),
                                                                         self.measurements)

    def is_complete(self):
        return self.battery is not None and self.prop is not None and self.measurements

def determine_indexes(reader):
    def set_measurement_attr(measurement_indexes, attr_name, colnr, cell):
        if getattr(measurement_indexes, attr_name) is not None:
            raise ValueError("Reached second {} field (containing '{}') at column {}, but previous "
                "measurement column group {} is incomplete.".format(attr_name, cell, col(colnr),
                                                                    measurement_indexes))
        setattr(measurement_indexes, attr_name, colnr)

    for rownr, row in enumerate(reader, start=1):
        indexes = RowIndexes()
        measurement_indexes = MeasurementIndexes()
        for i, cell in enumerate(row):
            if cell.lower().startswith("batt"):
                indexes.battery = i
            elif cell.lower().startswith("prop"):
                indexes.prop = i

            elif cell.lower().startswith("u"):
                set_measurement_attr(measurement_indexes, 'U', i, cell)
            elif cell.lower().startswith("i"):
                set_measurement_attr(measurement_indexes, 'I', i, cell)
            elif cell.lower().startswith("t"):
                set_measurement_attr(measurement_indexes, 'thrust', i, cell)
            elif cell.lower().startswith("rpm"):
                set_measurement_attr(measurement_indexes, 'rpm', i, cell)

            if measurement_indexes.is_complete():
                indexes.measurements.append(measurement_indexes)
                measurement_indexes = MeasurementIndexes()

        if indexes.is_complete():
            logging.debug("Found complete indexes {} on row {}.".format(indexes, rownr))
            return indexes
        else:
            logging.debug("Indexes {} based on row {} {} not complete, trying next row.".format(
                          indexes, rownr, row))

    raise ValueError("No complete indexes found.")

def load_motor_info_from_csv(motors, filepath):
    def read_measurement(row, indexes):
        try:
            return (float(row[indexes.U]), float(row[indexes.I]), float(row[indexes.thrust]))
        except ValueError as e:
            logging.debug("Failed to parse cells {} as measurement: {}".format([row[indexes.U], row[indexes.I], row[indexes.thrust]], e))
            return None

    with open(filepath, newline='') as csvfile:
        motor = os.path.splitext(os.path.basename(filepath))[0]
        reader = csv.reader(csvfile)
        indexof = determine_indexes(reader)

        for row in reader:
            for measurement in indexof.measurements:
                parsed = read_measurement(row, measurement)
                if parsed:
                    motors[motor][row[indexof.battery]][row[indexof.prop]].append(parsed)

    return motors

def load_motor_info():
    files = iglob('../*.csv')

    motors = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for filepath in files:
        try:
            load_motor_info_from_csv(motors, filepath)
        except ValueError as e:
            logging.error("Problem parsing file {}: {} - ignoring.".format(filepath, e))
    return motors

def save_data_for_webapp(motors, filepath):
    items = {
        'motor': set(),
        'cell': set(),
        'prop': set(),
        'esc': set(['TODO']),
        'author': set(['TODO'])
    }
    measurements = []

    l, m = (0, 0)
    for i, (motor, batteries) in enumerate(sorted(motors.items())):
        items['motor'].add(motor)
        for j, (battery, props) in enumerate(sorted(batteries.items())):
            items['cell'].add(battery)
            for k, (prop, values) in enumerate(sorted(props.items())):
                items['prop'].add(prop)
                measurements.append((1 << i, 1 << j, 1 << k, 1 << l, 1 << m))

    sorted_items = {key: sorted(values) for key, values in items.items()}
    json_data = {'items': sorted_items, 'measurements': measurements}
    with open(filepath, 'w') as outfile:
        json.dump(json_data, outfile, sort_keys=True, indent=4)

class RepeatCycler:
    def __init__(self, base_seq):
        self.base_iter = iter(base_seq)
        self.last = None

    def __iter__(self):
        return self

    def __next__(self):
        if self.last is not None:
            ret = self.last
            self.last = None
            return ret
        else:
            self.last = next(self.base_iter)
            return self.last

def plot_motor_params(motors):
    fig = plt.figure(1)
    ax1 = fig.add_subplot(111)

    color_cycle = ax1._get_lines.color_cycle
    ax1.set_color_cycle(RepeatCycler(color_cycle))

    for motor, batteries in sorted(motors.items()):
        for battery, props in sorted(batteries.items()):
            for prop, values in sorted(props.items()):
                name = "{}, {}, {}".format(motor, battery, prop)
                value_matrix = np.array([(0, 0, 0)] + values)
                x = value_matrix[:, 1]
                y = value_matrix[:, 2]
                ax1.plot(x, y, 'o', label=name)

                p = np.poly1d(np.polyfit(x, y, min(2, len(y)-1)))
                if len(y) > 2:
                    logging.info("Ratio at 50% max thrust:", p(0.5 * x[-1])/p(x[-1]))

                xp = np.linspace(0, np.max(x), 100)
                ax1.plot(xp, np.maximum(p(xp), 0), '--')

    ax1.grid(True)
    ax1.set_xlabel('I [A]')
    ax1.set_ylabel('thrust [g]')
    ax1.set_title('Motor Thrust')
    ax1.legend(loc='best')

    plt.show()

def main():
    motors = load_motor_info()
    save_data_for_webapp(motors, 'quad_plotter_webapp/templates/data.json')

    logging.debug(json.dumps(motors, sort_keys=True, indent=2))

    plot_motor_params(motors)

if __name__ == '__main__':
    main()
