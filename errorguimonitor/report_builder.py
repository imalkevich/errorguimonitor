#!/usr/bin/env python

"""
Report builder module.
"""

import inspect
import os
import pickle

from urllib.parse import quote as url_quote

from pyquery import PyQuery as pq

from .report_retriever import ErrorReportRetriever

TIME_FORMAT = '%Y_%m_%d_%H_%M'

class ErrorReportBuilder(object):
    def __init__(self, env, user, password):
        self.report_retriever = ErrorReportRetriever(env, user, password)

    def build_report(self, start_time, end_time):
        report_file_name = os.path.join(
            self._get_history_data_path(), 
            '{}__{}.pkl'.format(start_time.strftime(TIME_FORMAT), end_time.strftime(TIME_FORMAT))
        )
        
        if not os.path.isfile(report_file_name):
            report = self._load_report(start_time, end_time)
            pickle.dump(report, open(report_file_name, 'wb'))
        else:
            report = pickle.load(open(report_file_name, 'rb'))

        return report

    def _extract_error(self, tr, error_dict):
        app = tr('td:eq(1)').text().strip()
        key = tr('td:eq(2)').text().strip()
        occurrences = int(tr('td:eq(3)').text().strip())

        if app not in error_dict:
            error_dict[app] = {}

        if key not in error_dict[app]:
            error_dict[app][key] = occurrences

        return error_dict

    def _get_history_data_path(self):
        history_dir = os.path.join(
            '../',
            os.path.dirname(inspect.getfile(self.__class__)),
            'history_data')

        if not os.path.isdir(history_dir):
             os.makedirs(history_dir)

        return history_dir

    def _load_report(self, start_time, end_time):
        result = self.report_retriever.get_html(start_time, end_time)
        html = pq(result)

        return self._process_html(html)

    def _process_html(self, html):
        errors = {}
        trs = html('div.borderedBoxWhite table.tablesorter tr')[1:]
        for tr in trs:
            self._extract_error(pq(tr), errors)

        return errors

