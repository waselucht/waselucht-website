#!/usr/bin/env python
"""Mailer.

Usage:
  mailer.py send [--dry_run] [--incremental]
  mailer.py (-h | --help)

Options:
  -h --help      Show this screen.
  --dry-run      Dry run, do not send mails
  --incremental  Only mail report to new subscribers

"""
import datetime
from oauth2client.service_account import ServiceAccountCredentials
import gspread
import pandas as pd
import smtplib
from email.message import EmailMessage
from email.headerregistry import Address
from email.utils import make_msgid
import luftdaten
import os
import configparser
import report

def get_subscriptions(json_keyfile_name, sheet_name):
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']

    credentials = ServiceAccountCredentials.from_json_keyfile_name(
        json_keyfile_name, scope)

    gc = gspread.authorize(credentials)
    wks = gc.open(sheet_name).sheet1
    all_values = wks.get_all_values()
    df = pd.DataFrame.from_records(all_values[1:], columns=all_values[0])
    df.index = pd.to_datetime(df.iloc[:, 0])
    df = df.drop(columns=df.index.name)
    return df


def get_year_month():
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    if month == 1:
        month = 12;
        year = year - 1
    else:
        month = month - 1
    return year, month


def build_msg(sender, receiver, year, month, jpg_file_names):
    msg = EmailMessage()
    msg['Subject'] = 'fijn stof overzicht %s %d' % (report._MONTHS[month], year)
    msg['From'] = sender
    msg['To'] = receiver
    # msg.preamble = 'fijn stof overzicht'

    msg.set_content("""\
Overzicht voor pm2.5 en pm10 metingen Oktober 2018


De figuren zijn enkel te bekijken indien u html mail kan ontvangen.
    """)

    pm2p5_cid = make_msgid()
    pm10_cid = make_msgid()
    msg.add_alternative("""\
    <html>
      <head></head>
      <body>
        <img src="cid:{pm2p5_cid}" />
        <img src="cid:{pm10_cid}" />
      </body>
    </html>
    """.format(pm2p5_cid=pm2p5_cid[1:-1], pm10_cid=pm10_cid[1:-1]), subtype='html')


    cids = [pm2p5_cid, pm10_cid]
    for jpg_file_name, cid in zip(jpg_file_names, cids):
        with open(jpg_file_name, 'rb') as img:
            msg.get_payload()[1].add_related(img.read(), 'image', 'jpeg', cid=cid)

    return msg


def build_smtp_server(name, port):
    if port == 465:
        server = smtplib.SMTP_SSL('{}:{}'.format(name, port))
    else:
        server = smtplib.SMTP('{}:{}'.format(name, port))
        server.starttls() # this is for secure reason

    return server


def read_config():
    ini_file = os.getenv('MAILER_INI')
    if ini_file is None:
        raise RuntimeError('MAILER_INI env variable not set')

    config = configparser.ConfigParser()
    config.read(ini_file)

    return config


if __name__ == '__main__':
    from docopt import docopt
    import logging

    arguments = docopt(__doc__)

    logging.basicConfig(level=logging.INFO)
    try:
        cfg = read_config()
    except RuntimeError as e:
        logging.exception('Could not read config' + repr(e))

    subscriptions = get_subscriptions(cfg['gspread']['json_keyfile_name'],
                                      cfg['gspread']['sheet_name'])
    logging.info(subscriptions.describe())
    year, month = get_year_month()
    server = build_smtp_server(cfg['smtp_server']['name'],
                               cfg['smtp_server'].getint('port'))
    server.login(cfg['sender']['mailbox'], cfg['sender']['password'])
    sender = Address(cfg['sender']['display_name'],
                     cfg['sender']['username'],
                     cfg['sender']['domain'])
    sensor_ids = {}

    for index, row in subscriptions.iterrows():
        receiver, sensor_id = row

        if not (sensor_id in sensor_ids):
            sensor = luftdaten.Sensor(sensor_id)
            if sensor.metadata is None:
                logging.error('could not create sensor %s', sensor_id)
                continue
            logging.info('generate overview for sensor %s', sensor_id)

            figs = report.report_basic_month_overview(
                sensor, year, month, tz='Europe/Brussels')
            sensor_ids[sensor_id] = sorted(
                [fig.name + '.jpg' for fig in figs], reverse=True)
            for fig, name in zip(figs, sensor_ids[sensor_id]):
                fig.savefig(name)

        if arguments['--dry_run'] == False:
            logging.info('mail %s for sensor id %s', receiver, sensor_id)
            msg = build_msg(sender, receiver, year, month, sensor_ids[sensor_id])
            server.send_message(msg)

    server.quit()
