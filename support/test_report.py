from report import report_basic_month_overview
import luftdaten
import matplotlib.pyplot as plt

def test_report_basic_month_overview():
    for sensor in [luftdaten.Sensor(id) for id in ['12443', '10767']]:
        figs = report_basic_month_overview(
            sensor, 2018, 9, tz='Europe/Brussels')
        for fig in figs:
            fig.savefig(fig.name + '.jpg')
    plt.show()
