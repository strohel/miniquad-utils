#!/usr/bin/env python3

import numpy as np
import matplotlib.pyplot as plt


motors = {
    # motor name
    "Sunnysky X2204 2300KV": {
        # battery cells
        "3S": {
            # prop
            "6030": [
                # U [V], I [A], thrust [g]
                (12.2, 2.2, 120),
                (12.1, 8.5, 395),
            ],
            "6045": [
                (12, 4, 215),
                (11.7, 16.1, 560),
            ],
        },
    },
    "DYS BE1806 2300KV": {
        "3S": {
            "6030": [
                (12.1, 4, 240),
                (12, 10.2, 485),
            ],
            "6045": [
                (12, 5.1, 235),
                (11.8, 16.1, 580),
            ],
        }
    },
    "RCX H2205 2350KV": {
        "3S": {
            "6030": [
                (12.4, 10.8, 549),
            ],
            "6045": [
                (12.4, 18, 724),
            ],
        },
    },
    "RCX H2205 2633KV": {
        "3S": {
            "6030": [
                (12.5, 13.3, 632),
            ],
            "6045": [
                (12.4, 20.8, 796),
            ],
        }
    },
}

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

def main():
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
                #print("{}:\n{}\n".format(name, p))
                if len(y) > 2:
                    print("Ratio at 50% max thrust:", p(0.5 * x[-1])/p(x[-1]))

                xp = np.linspace(0, np.max(x), 100)
                ax1.plot(xp, np.maximum(p(xp), 0), '--')

    ax1.grid(True)
    ax1.set_xlabel('I [A]')
    ax1.set_ylabel('thrust [g]')
    ax1.set_title('Motor Thrust')
    ax1.legend(loc='best')

    plt.show()

if __name__ == '__main__':
    main()
