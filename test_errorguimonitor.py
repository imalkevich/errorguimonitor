#!/usr/bin/env python

""" Tests for errorguimonitor. """

import inspect
import os
import re
import sys
import unittest
import unittest.mock as mock

from datetime import datetime, timedelta
from pyquery import PyQuery as pq

from errorguimonitor import reporter, report_builder, report_retriever

class ErrorCompareReporterTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_get_report_dates_today_is_weekend(self):
        """ test today is Saturday, 6 days back """
        # arrange
        today = datetime(2018, 4, 7) + timedelta(hours=15)
        qed1week = reporter.ErrorCompareReporter('env', today)
        
        # act
        target_dates, history_dates = qed1week._get_report_dates(1, 5)

        # assert
        self.assertEqual(len(target_dates), 1)
        self.assertEqual(target_dates[0], (datetime(2018, 4, 6), datetime(2018, 4, 6, 23, 59, 59)))

        self.assertEqual(len(history_dates), 5)
        self.assertEqual(history_dates[0], (datetime(2018, 4, 5), datetime(2018, 4, 5, 23, 59, 59)))
        self.assertEqual(history_dates[1], (datetime(2018, 4, 4), datetime(2018, 4, 4, 23, 59, 59)))
        self.assertEqual(history_dates[2], (datetime(2018, 4, 3), datetime(2018, 4, 3, 23, 59, 59)))
        self.assertEqual(history_dates[3], (datetime(2018, 4, 2), datetime(2018, 4, 2, 23, 59, 59)))
        self.assertEqual(history_dates[4], (datetime(2018, 3, 30), datetime(2018, 3, 30, 23, 59, 59)))

    def test_get_report_dates(self):
        """ test today is Tuesday, 6 days back """
        # arrange
        today = datetime(2018, 4, 10) + timedelta(hours=8)
        qed1week = reporter.ErrorCompareReporter('env', today)
        
        # act
        target_dates, history_dates = qed1week._get_report_dates(1, 5)

        # assert
        self.assertEqual(len(target_dates), 1)
        self.assertEqual(target_dates[0], (datetime(2018, 4, 10), datetime(2018, 4, 10, 23, 59, 59)))

        self.assertEqual(len(history_dates), 5)
        self.assertEqual(history_dates[0], (datetime(2018, 4, 9), datetime(2018, 4, 9, 23, 59, 59)))
        self.assertEqual(history_dates[1], (datetime(2018, 4, 6), datetime(2018, 4, 6, 23, 59, 59)))
        self.assertEqual(history_dates[2], (datetime(2018, 4, 5), datetime(2018, 4, 5, 23, 59, 59)))
        self.assertEqual(history_dates[3], (datetime(2018, 4, 4), datetime(2018, 4, 4, 23, 59, 59)))
        self.assertEqual(history_dates[4], (datetime(2018, 4, 3), datetime(2018, 4, 3, 23, 59, 59)))

    def test_get_report(self):
        """ Test get report merged from multiple files into one """
        # arrange
        vals = {
            (datetime(2018, 4, 5), datetime(2018, 4, 5, 23, 59, 59)): { 'module_1': { 'a': 1, 'c': 1 }, 'module_2': { 'x': 1, 'y': 2 } }, 
            (datetime(2018, 4, 4), datetime(2018, 4, 4, 23, 59, 59)): { 'module_1': { 'b': 2, 'c': 2 }, 'module_2': { 'x': 2 } }
        }

        def side_effect(*args):
            return vals[args]

        mock_report_builder = report_builder.ErrorReportBuilder('env', 'user', 'password')
        mock_report_builder.build_report = mock.MagicMock(side_effect=side_effect)

        qed1week = reporter.ErrorCompareReporter('env', datetime.today())
        dates = [
            (datetime(2018, 4, 5), datetime(2018, 4, 5, 23, 59, 59)),
            (datetime(2018, 4, 4), datetime(2018, 4, 4, 23, 59, 59))
        ]
        
        # act
        report = qed1week._get_report(mock_report_builder, dates)

        # assert
        self.assertEqual(report, { 'module_1': { 'a': [1], 'b': [2], 'c': [1, 2] }, 'module_2': { 'x': [1, 2], 'y': [2] } })

    def test_check_error_rate_increase(self):
        # arrange
        qed1week = reporter.ErrorCompareReporter('env', datetime.today())
        target_errors = [10]
        history_errors = [5]

        # act
        conf_int_diff = qed1week._check_error_rate_increase(target_errors, history_errors)

        # assert
        self.assertTrue(conf_int_diff[0] > 0)

    def test_prepare_report(self):
        # arrange
        qed1week = reporter.ErrorCompareReporter('env', datetime.today())
        target_report = { 
            'Document': { 'doc_key': [1] },
            'Website': { 'error_key_1': [1], 'error_key_2': [2], 'error_key_3': [3] }
        }

        history_report = { 
            'Document': { 'doc_key': [1] },
            'Website': { 'error_key_2': [2, 3, 4, 5], 'error_key_3': [3, 4] }
        }

        def side_effect(target_errors_count, history_errors_count):
            if target_errors_count == [2] \
                and history_errors_count == [2, 3, 4, 5]:
                return [1.0, 2.0]
            elif target_errors_count == [3] \
                and history_errors_count == [3, 4]:
                return [0.0, 0.5]
            
            raise ValueError('unexpected arguments')

        qed1week._check_error_rate_increase = mock.MagicMock(side_effect=side_effect)

        # act
        (new_errors, errors_increased) = qed1week._prepare_report(target_report, history_report)

        # assert
        self.assertEqual(new_errors, { 'error_key_1': [1] })
        self.assertEqual(errors_increased, { 'error_key_2': [1.0, 2.0] })

    def test_create_notification(self):
        # arrange
        qed1week = reporter.ErrorCompareReporter('env', datetime.today())

        target_dates = [
            (datetime(2018, 4, 9), datetime(2018, 4, 9, 23, 59, 59))
        ]

        history_dates = [
            (datetime(2018, 4, 6), datetime(2018, 4, 6, 23, 59, 59)),
            (datetime(2018, 4, 5), datetime(2018, 4, 5, 23, 59, 59))
        ]

        new_errors = { 'error_key_1': [1] }
        errors_increased = { 'error_key_2': [1.0, 2.0], 'error_key_3': [.5, .8] }

        # act
        (subject, body) = qed1week._create_notification(target_dates, history_dates, new_errors, errors_increased)

        # assert
        self.assertTrue(len(subject) > 0)
        self.assertTrue(len(body) > 0)

    @mock.patch('errorguimonitor.reporter.smtplib')
    def test_send_notification(self, mock_smtplib):
        # arrange
        qed1week = reporter.ErrorCompareReporter('env', datetime.today())

        mock_server = mock.MagicMock()
        dummySMTP = mock.MagicMock(return_value=mock_server)

        mock_smtplib.SMTP = dummySMTP

        # act
        qed1week._send_notification('Test email', 'Test email body', 'smtp_user', 'smtp_password', ['ihar.malkevich@thomsonreuters.com'])

        # assert
        mock_smtplib.SMTP.assert_called_with('smtp.gmail.com', 587)
        mock_server.ehlo.assert_called_once()
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_with('smtp_user', 'smtp_password')
        mock_server.send_message.assert_called_once()
        mock_server.quit.assert_called_once()

class ErrorReportBuilderTestCase(unittest.TestCase):
    def setUp(self):
        pass

    def tearDown(self):
        pass

    def test_load_report(self):
        # arrange
        builder = report_builder.ErrorReportBuilder('some_env', 'user', 'password')

        builder.report_retriever.get_html = mock.MagicMock(return_value='<html></html>')
        builder._process_html = mock.MagicMock(return_value={ 'module': { 'key': 1 } })

        start_time = datetime(2018, 4, 8)
        end_time = datetime(2018, 4, 8, 23, 59, 59)

        # act
        report = builder._load_report(start_time, end_time)

        # assert
        self.assertEqual(report, { 'module': { 'key': 1 } })

        
        builder.report_retriever.get_html.assert_called_with(start_time, end_time)

    def test_process_html(self):
        # arrange
        builder = report_builder.ErrorReportBuilder('some_env', 'user', 'password')

        html_path = os.path.join(
            os.path.dirname(inspect.getfile(self.__class__)),
            'test_fixture',
            'sample_errorgui_page.html')

        with open(html_path, 'r') as f:
            content = f.read()

        html = pq(content)

        # act
        report = builder._process_html(html)

        # assert
        self.assertEqual(
            report, 
            {
                'Document': { 'document_error_key_1': 1, 'document_error_key_2': 2 },
                'Search': { 'search_error_key': 2 },
                'Website': { 'website_error_key_1': 3, 'website_error_key_2': 5 }
            }
        )

    @mock.patch('errorguimonitor.report_builder.os')    
    def test_get_history_data_path_dir_not_exist(self, mock_os):
        # arrange
        builder = report_builder.ErrorReportBuilder('some_env', 'user', 'password')
        mock_os.path.join.return_value = 'history_data'
        mock_os.path.isdir.return_value = False
        mock_os.makedirs.return_value = True

        # act
        history_dir = builder._get_history_data_path()

        # assert
        expected_dir = 'history_data'
        self.assertEqual(history_dir, expected_dir)

        mock_os.path.isdir.assert_called_with(expected_dir)
        mock_os.makedirs.assert_called_with(expected_dir)

    @mock.patch('errorguimonitor.report_builder.os')
    def test_get_history_data_path_dir_exist(self, mock_os):
        # arrange
        mock_os.path.join.return_value = 'history_data'
        mock_os.path.isdir.return_value = True
        mock_os.makedirs.return_value = False

        builder = report_builder.ErrorReportBuilder('some_env', 'user', 'password')

        # act
        history_dir = builder._get_history_data_path()

        # assert
        expected_dir = 'history_data'
        self.assertEqual(history_dir, expected_dir)

        mock_os.path.isdir.assert_called_with(expected_dir)
        self.assertFalse(mock_os.makedirs.called)

    @mock.patch('errorguimonitor.report_builder.os')
    @mock.patch('errorguimonitor.report_builder.pickle')
    @mock.patch('errorguimonitor.report_builder.open')
    def test_build_report_no_report_exist(self, mock_open, mock_pickle, mock_os):
        # arrange
        builder = report_builder.ErrorReportBuilder('some_env', 'user', 'password')

        builder._get_history_data_path = mock.MagicMock(return_value='history_data')
        builder._load_report = mock.MagicMock(return_value={ 'module': { 'key': 1 } })

        mock_os.path.join.return_value = 'path_does_not_exist'
        mock_os.path.isfile.return_value = False

        mock_pickle.dump.return_value = True

        mock_open.return_value = True

        start_time = datetime(2018, 4, 8)
        end_time = datetime(2018, 4, 8, 23, 59, 59)

        # act
        report = builder.build_report(start_time, end_time)

        # assert
        self.assertEqual(report, { 'module': { 'key': 1 } })

        mock_os.path.join.assert_called_with('history_data', '2018_04_08_00_00__2018_04_08_23_59.pkl')
        mock_os.path.isfile.assert_called_with('path_does_not_exist')
        builder._load_report.assert_called_with(start_time, end_time)
        mock_open.assert_called_with('path_does_not_exist', 'wb')
        mock_pickle.dump.assert_called_with(report, True)

    @mock.patch('errorguimonitor.report_builder.os')
    @mock.patch('errorguimonitor.report_builder.pickle')
    @mock.patch('errorguimonitor.report_builder.open')
    def test_build_report_report_exist(self, mock_open, mock_pickle, mock_os):
        # arrange
        builder = report_builder.ErrorReportBuilder('some_env', 'user', 'password')

        builder._get_history_data_path = mock.MagicMock(return_value='history_data')

        mock_os.path.join.return_value = 'path_exists'
        mock_os.path.isfile.return_value = True

        mock_pickle.load.return_value = { 'module': { 'key': 1 } }

        mock_open.return_value = True

        start_time = datetime(2018, 4, 8)
        end_time = datetime(2018, 4, 8, 23, 59, 59)

        # act
        report = builder.build_report(start_time, end_time)

        # assert
        self.assertEqual(report, { 'module': { 'key': 1 } })

        mock_os.path.join.assert_called_with('history_data', '2018_04_08_00_00__2018_04_08_23_59.pkl')
        mock_os.path.isfile.assert_called_with('path_exists')
        mock_open.assert_called_with('path_exists', 'rb')
        mock_pickle.load.assert_called_with(True)

class ErrorReportRetrieverTestCase(unittest.TestCase):
    def test_get_error_gui_url(self):
        # arrange
        start_time = datetime(2018, 4, 8)
        end_time = datetime(2018, 4, 8, 23, 59, 59)
        
        retriever = report_retriever.ErrorReportRetriever('QED', 'user', 'password')

        # act
        url = retriever._get_error_gui_url(start_time, end_time)

        # assert
        expected_url = (
            "http://cobalttools.qed.int.westgroup.com/ErrorGUINext/initialResults.do?search=y&param=&qS=&a=&b=&c=&d=&e=&f=&g=&h=&i=&j=&x=&y=&z=&v=&"
            "environs=QED&view=summary&site=all&start_time=2018-04-08%2000%3A00&end_time=2018-04-08%2023%3A59&submitForm=Submit"
        )
        self.assertEqual(url, expected_url)

    '''
    @mock.patch('errorguimonitor.report_retriever.requests')
    def test_get_html(self, mock_requests):
        # arrange
        start_time = datetime(2018, 4, 8)
        end_time = datetime(2018, 4, 8, 23, 59, 59)
        


        retriever = report_retriever.ErrorReportRetriever('QED', 'user', 'password')

        # act
        html = retriever.get_html(start_time, end_time)

        # assert
        self.assertIsNotNone(html)
    '''

if __name__ == '__main__':
    unittest.main()