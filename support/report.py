import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from calendar import monthrange
import pandas as pd
import luftdaten

# TODO use locale to get abrivated weekdays and month names
_WEEKDAYS = {0: 'ma',
             1: 'di',
             2: 'wo',
             3: 'do',
             4: 'vr',
             5: 'za',
             6: 'zo'}

_MONTHS = {1: 'januari',
           2: 'februari',
           3: 'maart',
           4: 'april',
           5: 'mei',
           6: 'juni',
           7: 'juli',
           8: 'augustus',
           9: 'september',
           10: 'oktober',
           11: 'november',
           12: 'december'}

_BINS = {'irceline': {'pm10': ('µg/m³', (10, 20, 30, 40, 50, 60, 70, 80, 100)),
                      'pm2.5': ('µg/m³', (5, 10, 15, 20, 25, 35, 40, 50, 60))}}

_WHO_GUIDELINE = {'daily': {'pm10': (50, 'µg/m³'), 'pm2.5': (25, 'µg/m³')}}

# colors taken from respective website using https://imagecolorpicker.com
_BIN_COLORS = {'irceline': ('#0001FA',
                            '#009AFD',
                            '#019A00',
                            '#00FF02',
                            '#FFFF02',
                            '#FFBB00',
                            '#FF6502',
                            '#FE0000',
                            '#9C0004',
                            '#650002')}

def _get_bin(x, bins):
    unit, bins_ = bins
    bin_ = 0
    for threshold in bins_:
        if (x < threshold):
            break
        bin_ = bin_ + 1
    return bin_


def _get_rolling_daily_max(sensor, start_date, end_date, window, tz):
    # TODO check for center of window and min_periods
    sensor.get_measurements(start_date=start_date, end_date=end_date)
    if tz:
        index = sensor.measurements.index.tz_convert(tz)
        sensor.measurements.index = index
    r24h = sensor.measurements.rolling(window).mean()
    rdm = r24h.groupby(pd.Grouper(freq='D')).max()
    return rdm


def _plot_basic_month_phenomena_overview(rdm, bins, colors, who_guideline):
    fig = plt.figure(figsize=(5.83, 8.27))
    ax = fig.add_axes([0, 0, 1, 1], frameon=False, aspect=1)
    ax.set_xbound(lower=-1.0, upper=7.0)
    ax.set_ybound(lower=-7.0, upper=1.5)
    ax.axis('off')

    for i in range(7):
        plt.text(i, .70, _WEEKDAYS[i], horizontalalignment='center',
                 verticalalignment='center')

    # draw each day
    y = 0
    r_outer_circle = 0.4
    r_inner_circle = 0.2
    for timestamp, data in rdm.iteritems():
        x = timestamp.weekday()
        if not pd.isna(data):
            bin_ = _get_bin(data, bins)
            p = mpatches.Circle((x, y), r_outer_circle, color=colors[bin_])
            ax.add_patch(p)
            p = mpatches.Circle((x, y), r_inner_circle, color='white')
            ax.add_patch(p)
        plt.text(x, y, str(timestamp.day), horizontalalignment='center',
                 verticalalignment='center', color='black')
        if (x == 6):
            y = y - 1

    delta = (6 + 2.0 * r_outer_circle) / len(colors)
    for i, color in enumerate(colors):
        p = mpatches.Rectangle(xy=(i * delta - r_outer_circle, -6.5),
                               width=delta * 0.90,
                               height=delta/2.0,
                               color=color)
        ax.add_patch(p)

    # add bin color info and WHO guideline
    # assumption is that WHO falls in bin boundary
    # quick and dirty
    y = -6.75
    plt.text(-r_outer_circle, y, str(0), horizontalalignment='center')
    for i, bin_ in enumerate(bins[1]):
        x = (i + 1) * delta - r_outer_circle
        plt.text(x, y, str(bin_), horizontalalignment='center')
        if bin_ == who_guideline:
            plt.text(x, y - .5, 'WHO advieswaarde', horizontalalignment='center')
            p = mpatches.Arrow(x, y - .3, 0, .25, width=.2)
            ax.add_patch(p)
    plt.text((i + 2) * delta - r_outer_circle, y, '[%s]' % bins[0],
                horizontalalignment='center')

    return fig, ax


def report_basic_month_overview(sensor, year, month, bins=None, colors=None,
                                tz=None):
    bins = _BINS['irceline'] if bins is None else bins
    colors = _BIN_COLORS['irceline'] if colors is None else colors
    tz = 'UTC' if tz is None else tz

    _, nb_days = monthrange(year, month)
    rdm = _get_rolling_daily_max(sensor,
                                 start_date='%d-%d-1' % (year, month),
                                 end_date='%d-%d-%d' % (year, month, nb_days),
                                 window='24h',
                                 tz=tz)
    figs = []
    for phenomenon in sensor.phenomena:
        fig, ax = _plot_basic_month_phenomena_overview(
                      rdm[phenomenon],
                      bins[phenomenon],
                      colors,
                      _WHO_GUIDELINE['daily'][phenomenon][0])
        ax.set_title("%s, %d\n\n max$|%s|_{24u}$   %s-%s" % (
            _MONTHS[month], year, phenomenon.upper(), sensor.sensor_type,
            sensor.sensor_id))
        fig.name = "%d-%02d_%s-%s_%s" % (year,
                                          month,
                                          sensor.sensor_type,
                                          sensor.sensor_id,
                                          phenomenon)
        figs.append(fig)

    return figs
