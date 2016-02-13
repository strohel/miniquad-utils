#!/usr/bin/env python3

from collections import defaultdict
import csv
from glob import iglob
import json
import logging
import math
import os

import numpy as np
import matplotlib.pyplot as plt


def col(colindex):
    if colindex is None:
        return '?'
    return chr(ord('A') + colindex)

class Measurement:
    def __init__(self, U=None, I=None, thrust=None, rpm=None):
        self.U = U
        self.I = I
        self.thrust = thrust
        self.rpm = rpm

    def __repr__(self, args=None, name='Measurement'):
        if not args:
            args = (self.U, self.I, self.thrust, self.rpm)
        return "{}(U={}, I={}, thrust={}, rpm={})".format(name, *args)

    @classmethod
    def from_row(cls, indexof, row):
        """Returns None if fails to parse data in \p row as floating point numbers"""
        try:
            return cls(float(row[indexof.U]), float(row[indexof.I]), float(row[indexof.thrust]),
                       None if not row[indexof.rpm] else float(row[indexof.rpm]))
        except ValueError as e:
            logging.debug("Failed to parse cells {} as measurement: {}".format([row[indexof.U],
                          row[indexof.I], row[indexof.thrust], row[indexof.rpm]], e))

class MeasurementIndexes(Measurement):
    def __repr__(self):
        args = (col(self.U), col(self.I), col(self.thrust), col(self.rpm))
        return Measurement.__repr__(self, args, 'MeasurementIndexes')

    def is_complete(self):
        return self.U is not None and self.I is not None \
               and self.thrust is not None and self.rpm is not None


class Setup:
    def __init__(self, motor=None, cells=None, prop=None, esc=None, author=None, session=None):
        self.motor = motor
        self.cells = cells
        self.prop = prop
        self.esc = esc
        self.author = author
        self.session = session

    @classmethod
    def from_row(cls, indexof, motor, row):
        return cls(motor, row[indexof.cells], row[indexof.prop], row[indexof.esc],
                   row[indexof.author], row[indexof.session])

    def __repr__(self, args=None, name='Setup'):
        if not args:
            args = (self.motor, self.cells, self.prop, self.esc, self.author, self.session)
        return "{}(motor={}, cells={}, prop={}, esc={}, author={}, session={})".format(name, *args)

class SetupIndexes(Setup):
    def __repr__(self):
        args = ('TBA', col(self.cells), col(self.prop), col(self.esc), col(self.author), col(self.session))
        return Setup.__repr__(self, args, 'SetupIndexes')

    def is_complete(self):
        return self.cells is not None and self.prop is not None and self.esc is not None \
               and self.author is not None and self.session is not None


def determine_indexes(reader):
    csv_to_setup = {key: key for key in ['cells', 'prop', 'esc', 'author', 'session']}
    csv_to_measurement = {'u': 'U', 'i': 'I', 't': 'thrust', 'rpm': 'rpm'}

    def match_setup_column(indexes, colnr, cell):
        for csv_key, setup_key in csv_to_setup.items():
            if cell.lower().startswith(csv_key):
                if getattr(indexes, setup_key) is not None:
                    raise ValueError("Reached second {} field (containing '{}') at column {}.".
                                        format(csv_key, cell, col(colnr)))
                setattr(indexes, setup_key, colnr)
                return True

    def match_measurement_column(measurement_indexes, colnr, cell):
        for csv_key, measurement_key in csv_to_measurement.items():
            if cell.lower().startswith(csv_key):
                if getattr(measurement_indexes, measurement_key) is not None:
                    raise ValueError("Reached second {} field (containing '{}') at column {}, but previous "
                        "measurement column group {} is incomplete.".format(csv_key, cell, col(colnr),
                                                                            measurement_indexes))
                setattr(measurement_indexes, measurement_key, colnr)
                return True

    for rownr, row in enumerate(reader, start=1):
        setup_indexes = SetupIndexes()
        measurement_idx_list = []
        measurement_indexes = MeasurementIndexes()
        for i, cell in enumerate(row):
            if match_setup_column(setup_indexes, i, cell):
                pass
            elif match_measurement_column(measurement_indexes, i, cell):
                pass
            else:
                logging.debug("Column {} (containing '{}') did not match any expected header.".
                              format(col(i), cell))

            if measurement_indexes.is_complete():
                measurement_idx_list.append(measurement_indexes)
                measurement_indexes = MeasurementIndexes()

        if setup_indexes.is_complete() and measurement_idx_list:
            logging.info("Found complete indexes {} (and measurement indexes {}) on row {}.".format(
                         setup_indexes, measurement_idx_list, rownr))
            return setup_indexes, measurement_idx_list
        else:
            logging.debug('Indexes {} (and measurement indexes {}) based on row {} {} not complete, '
                          'trying next row.'.format(setup_indexes, measurement_idx_list, rownr, row))

    raise ValueError("No complete indexes found.")

def load_motor_info_from_csv(measurement_map, filepath):
    with open(filepath, newline='') as csvfile:
        motor = os.path.splitext(os.path.basename(filepath))[0]
        reader = csv.reader(csvfile)
        setup_indexes, measurement_idx_list = determine_indexes(reader)

        for row in reader:
            setup = Setup.from_row(setup_indexes, motor, row)
            for measurement_indexes in measurement_idx_list:
                measurement = Measurement.from_row(measurement_indexes, row)
                if not measurement:
                    continue
                measurement_map[setup].append(measurement)

    return measurement_map

def load_motor_info():
    files = iglob('csv/*.csv')

    measurement_map = defaultdict(list)
    for filepath in files:
        try:
            load_motor_info_from_csv(measurement_map, filepath)
        except ValueError as e:
            logging.error("Problem parsing file {}: {} Skipping file.".format(filepath, e))
    return measurement_map

def determine_unique_setup_keys(measurement_map):
    unique_keys = Setup(set(), set(), set(), set(), set(), set())
    for setup in measurement_map.keys():
        unique_keys.motor.add(setup.motor)
        unique_keys.cells.add(setup.cells)
        unique_keys.prop.add(setup.prop)
        unique_keys.esc.add(setup.esc)
        unique_keys.author.add(setup.author)
        unique_keys.session.add(setup.session)

    unique_keys.motor = sorted(unique_keys.motor)
    unique_keys.cells = sorted(unique_keys.cells)
    unique_keys.prop = sorted(unique_keys.prop)
    unique_keys.esc = sorted(unique_keys.esc)
    unique_keys.author = sorted(unique_keys.author)
    unique_keys.session = sorted(unique_keys.session)

    return unique_keys

def index_measurement_map(unique_setup_keys, measurement_map):
    """Transform string-key-based measurement map to index-key-based measurement map."""
    index_map = {}
    for setup, measurements in measurement_map.items():
        indexed_setup = Setup(
            1 << unique_setup_keys.motor.index(setup.motor),
            1 << unique_setup_keys.cells.index(setup.cells),
            1 << unique_setup_keys.prop.index(setup.prop),
            1 << unique_setup_keys.esc.index(setup.esc),
            1 << unique_setup_keys.author.index(setup.author),
            1 << unique_setup_keys.session.index(setup.session))
        index_map[indexed_setup] = measurements
    return index_map

def save_data_for_webapp(unique_setup_keys, index_map, filepath):
    items = unique_setup_keys.__dict__
    measurements = [(setup.motor, setup.cells, setup.prop, setup.esc, setup.author, setup.session)
                    for setup in index_map]

    json_data = {'items': items, 'measurements': measurements}
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

def plot_motor_params(unique_setup_keys, index_map):
    types = ("motor", "cells", "prop", "esc", "author")

    fig = plt.figure(1)
    ax1 = fig.add_subplot(111)

    color_cycle = ax1._get_lines.color_cycle
    ax1.set_color_cycle(RepeatCycler(color_cycle))

    title = ['Motor Thrust']
    # filter measurements, save to index_map
    filtered_unique_keys = determine_unique_setup_keys(index_map)
    for type in types:
        if len(getattr(filtered_unique_keys, type)) < 2:
            title.append(getattr(unique_setup_keys, type)[0])

    import pprint
    pprint.pprint(filtered_unique_keys)

    for setup, measurements in index_map.items():
        label = []
        for type in types:
            if len(getattr(filtered_unique_keys, type)) >= 2:
                type_index = int(math.log2(getattr(setup, type)))
                label.append(getattr(unique_setup_keys, type)[type_index])

        value_matrix = np.array([(0, 0, 0)] + [(m.U, m.I, m.thrust) for m in measurements])
        x = value_matrix[:, 1]
        y = value_matrix[:, 2]
        ax1.plot(x, y, 'o', label=', '.join(label))

        p = np.poly1d(np.polyfit(x, y, min(2, len(y)-1)))
        if len(y) > 2:
            logging.info("Ratio at 50% max thrust: {}".format((0.5 * x[-1])/p(x[-1])))

        xp = np.linspace(0, np.max(x), 100)
        ax1.plot(xp, np.maximum(p(xp), 0), '--')

    ax1.grid(True)
    ax1.set_xlabel('I [A]')
    ax1.set_ylabel('thrust [g]')
    ax1.set_title(', '.join(title))
    ax1.legend(loc='best')

    plt.tight_layout()
    plt.show()

def main():
    logging.basicConfig(level=logging.DEBUG)

    measurement_map = load_motor_info()
    unique_setup_keys = determine_unique_setup_keys(measurement_map)
    index_map = index_measurement_map(unique_setup_keys, measurement_map)
    save_data_for_webapp(unique_setup_keys, index_map, 'quad_plotter_webapp/templates/data.json')
    plot_motor_params(unique_setup_keys, index_map)

if __name__ == '__main__':
    main()
