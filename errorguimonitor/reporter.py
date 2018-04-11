#!/usr/bin/env python

"""
Reports module for different kind of reports.
"""
import argparse
import numpy as np
import smtplib

from datetime import datetime, timedelta
from email.message import EmailMessage

from prettytable import PrettyTable

from . import __version__
from .report_builder import ErrorReportBuilder

WORKING_DAYS_CURRENT_COUNT = 1
WORKING_DAYS_PRIOR_COUNT = 5
DATE_FORMAT = '%Y-%m-%d'
RECIPIENTS = ['ihar.malkevich@thomsonreuters.com']

class ErrorCompareReporter(object):
    """
    Error compare reporter - compares periods and reports new errors or error rates increase.
    """
    def __init__(self, env, date, safeid_user, safeid_password, smtp_user, smtp_password):
        self.env = env
        self.today = date
        self.safeid_user = safeid_user
        self.safeid_password = safeid_password
        self.smtp_user = smtp_user
        self.smtp_password = smtp_password

    def run(self):
        target_dates, history_dates = self._get_report_dates(WORKING_DAYS_CURRENT_COUNT, WORKING_DAYS_PRIOR_COUNT)
        
        report_builder = ErrorReportBuilder(self.env, self.safeid_user, self.safeid_password)

        target_report = self._get_report(report_builder, target_dates)
        history_report = self._get_report(report_builder, history_dates)

        (new_errors, errors_increased) = self._prepare_report(target_report, history_report)

        (subject, body) = self._create_notification(target_dates, history_dates, new_errors, errors_increased)

        self._send_notification(subject, body, self.smtp_user, self.smtp_password, RECIPIENTS)

    def _check_error_rate_increase(self, target_errors, history_errors):
        target_median_scores = map(np.median, self._get_bootstrap_samples(np.array(target_errors), 100))
        history_median_scores = map(np.median, self._get_bootstrap_samples(np.array(history_errors), 100))

        delta_median = [x[0] - x[1] for x in zip(target_median_scores, history_median_scores)]
        conf_int_diff = self._stat_intervals(delta_median, 0.05)

        return conf_int_diff

    def _create_notification(self, target_dates, history_dates, new_errors, errors_increased):
        dates_to = '|'.join([date[0].strftime(DATE_FORMAT) for date in target_dates])
        dates_compare = '|'.join([date[0].strftime(DATE_FORMAT) for date in history_dates])

        subject = 'Error report for Website for {} v. {}'.format(dates_to, dates_compare)

        body = ''

        tbl_attr = { 
            'style': 'border: 1px solid black; border-collapse: collapse;',
            'cellpadding': 5,
            'border': 1
        }
        if len(new_errors):
            body += 'New errors observed:<br/>'
            tbl = PrettyTable()
            tbl.field_names = ['Error key', 'Occurrences']
            for key in new_errors:
                tbl.add_row([key, ', '.join([str(val) for val in new_errors[key]])])

            tbl.align["Error key"] = "l"
            body += tbl.get_html_string(attributes=tbl_attr)
        else:
            body += 'No new errors observed.<br/>'

        body += '<br/><br/>'

        if len(errors_increased):
            body += 'Errors increased:<br/>'
            tbl = PrettyTable()
            tbl.field_names = ['Error key', 'Increase rate*']
            for key in errors_increased:
                tbl.add_row([key, ' - '.join([str(round(val, 0)) for val in errors_increased[key]])])

            tbl.align["Error key"] = "l"
            body += tbl.get_html_string(attributes=tbl_attr)

            body += '<br/>* 95% confidence interval for the difference between medians'
        else:
            body += 'No errors increased observed.<br/>'

        body += '<br/><br/>Thanks'

        return (subject, body)

    def _get_bootstrap_samples(self, data, n_samples):
        indices = np.random.randint(0, len(data), (n_samples, len(data)))
        samples = data[indices]
        return samples

    def _get_report(self, report_builder, dates):
        errors = dict()
        for (start_date, end_date) in dates:
            report = report_builder.build_report(start_date, end_date)
            for module in report:
                if not module in errors:
                    errors[module] = {}

                for error in report[module]:
                    if error in errors[module]:
                        errors[module][error].append(report[module][error])
                    else:
                        errors[module][error] = [report[module][error]]

        return errors

    def _get_report_dates(self, target_days_count, history_dates_count):
        report_dates = list()

        days_collected = 0
        days_look_back = 0

        days_count = target_days_count + history_dates_count

        while days_collected < days_count:
            report_date = self.today + timedelta(days=days_look_back)
            adjust_date = False

            if report_date.weekday() == 6:
                days_look_back -= 2
                adjust_date = True
            elif report_date.weekday() == 5:
                days_look_back -= 1
                adjust_date = True

            if adjust_date == True:
                report_date = self.today + timedelta(days=days_look_back)

            start_date = datetime(report_date.year, report_date.month, report_date.day)
            end_date = datetime(report_date.year, report_date.month, report_date.day) + timedelta(hours=23, minutes=59, seconds=59)

            report_dates.append((start_date, end_date))
            
            days_collected += 1
            days_look_back -= 1

        target_dates = report_dates[:WORKING_DAYS_CURRENT_COUNT]
        history_dates = report_dates[WORKING_DAYS_CURRENT_COUNT:]

        return (target_dates, history_dates)

    def _prepare_report(self, target_report, history_report):
        errors_target = target_report['Website']
        errors_history = history_report['Website']

        new_errors = {}
        errors_increased = {}

        for key in errors_target:
            if not key in errors_history:
                new_errors[key] = errors_target[key]
            else:
                target_errors_count = errors_target[key] 
                history_errors_count = errors_history[key]

                conf_int_diff = self._check_error_rate_increase(target_errors_count, history_errors_count)
                if conf_int_diff[0] > 0:
                    errors_increased[key] = conf_int_diff

        return (new_errors, errors_increased)

    def _send_notification(self, subject, body, smtp_user, smtp_password, to, cc=None, bcc=None):
        msg = EmailMessage()

        msg['Subject'] = subject
        msg.set_content(body)
        msg['From'] = 'errorguimonitor@test.com'
        msg['To'] = ', '.join(to)
        msg.replace_header('Content-type', 'text/html')
        if cc:
            msg['Cc'] = ', '.join(cc)
        if bcc:
            msg['Bcc'] = ', '.join(bcc)

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.ehlo()
        server.starttls()
        server.login(smtp_user, smtp_password)
        server.send_message(msg)
        server.quit()

    def _stat_intervals(self, stat, alpha):
        boundaries = np.percentile(stat, [100 * alpha / 2., 100 * (1 - alpha / 2.)])
        return boundaries

def get_parser():
    parser = argparse.ArgumentParser(description='compare errors for two periods in s specific environment via the command line')

    parser.add_argument('-e', '--environment', help='the environment (QED only at the moment)', type=str)
    parser.add_argument('-d', '--date', help='the target date (year-month-day)', type=str)
    parser.add_argument('-u', '--user', help='SAFE ID user', type=str)
    parser.add_argument('-p', '--password', help='SAFE ID password', type=str)
    parser.add_argument('-smtp_user', '--smtp_user', help='Gmail account username', type=str)
    parser.add_argument('-smtp_password', '--smtp_password', help='Gmail account password', type=str)

    parser.add_argument('-v', '--version', help='displays the current version of errorguimonitor',
                        action='store_true')

    return parser

def command_line_runner():
    parser = get_parser()
    args = vars(parser.parse_args())

    if args['version']:
        print(__version__)
        return

    if not args['environment'] \
        or not args['date']:
        parser.print_help()
        return

    env = args['environment']
    try:
        target_date = datetime.strptime(args['date'], DATE_FORMAT)
    except ValueError:
        print('incorrect date provided. Please use year-month-day format')
        return

    safe_id_user = args['user']
    safe_id_password = args['password']
    smtp_user = args['smtp_user']
    smtp_password = args['smtp_password']

    if not safe_id_user \
        or not safe_id_password \
        or not smtp_user \
        or not smtp_password:
        print('Please provide usernames and passwords to successfully run the utility.')
        parser.print_help()
        return
    
    reporter = ErrorCompareReporter(env, target_date, safe_id_user, safe_id_password, smtp_user, smtp_password)
    reporter.run()

if __name__ == '__main__':
    command_line_runner()

