# coding=utf-8
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.
# pylint: disable=protected-access
from os.path import join as pathjoin

from pytest import raises

from sapphire import Sapphire, SERVED_ALL, SERVED_NONE, SERVED_REQUEST, SERVED_TIMEOUT, ServerMap

from .reporter import Report
from .runner import _IdleChecker, Runner, RunResult
from .storage import TestCase
from ..target import Target, TargetLaunchError, TargetLaunchTimeout

def test_runner_01(mocker, tmp_path):
    """test Runner()"""
    fake_time = mocker.patch("grizzly.common.runner.time", autospec=True)
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)
    target.detect_failure.return_value = target.RESULT_NONE
    runner = Runner(server, target)
    assert runner._idle is None
    serv_files = ["a.bin", "/another/file.bin"]
    testcase = mocker.Mock(spec=TestCase, landing_page=serv_files[0], optional=[])
    # all files served
    fake_time.side_effect = (1, 2)
    server.serve_path.return_value = (SERVED_ALL, serv_files)
    result = runner.run([], ServerMap(), testcase)
    assert result.duration == 1
    assert result.status == RunResult.COMPLETE
    assert result.served == serv_files
    assert not result.timeout
    assert target.close.call_count == 0
    assert target.dump_coverage.call_count == 0
    assert testcase.dump.call_count == 1
    # some files served
    fake_time.side_effect = (1, 2)
    server.serve_path.return_value = (SERVED_REQUEST, serv_files)
    result = runner.run([], ServerMap(), testcase, coverage=True)
    assert result.status == RunResult.COMPLETE
    assert result.served == serv_files
    assert not result.timeout
    assert target.close.call_count == 0
    assert target.dump_coverage.call_count == 1
    # existing test path
    fake_time.side_effect = (1, 2)
    testcase.reset_mock()
    tc_path = (tmp_path / "tc")
    tc_path.mkdir()
    server.serve_path.return_value = (SERVED_ALL, serv_files)
    result = runner.run([], ServerMap(), testcase, test_path=str(tc_path))
    assert result.status == RunResult.COMPLETE
    assert target.close.call_count == 0
    assert testcase.dump.call_count == 0
    tc_path.is_dir()

def test_runner_02(mocker):
    """test Runner() errors"""
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)
    testcase = mocker.Mock(spec=TestCase, landing_page="x", optional=[])
    runner = Runner(server, target)
    # no files served
    server.serve_path.return_value = (SERVED_NONE, [])
    target.detect_failure.return_value = target.RESULT_NONE
    result = runner.run([], ServerMap(), testcase)
    assert result.status == RunResult.ERROR
    assert not result.served
    assert not result.timeout
    assert target.close.call_count == 1
    target.reset_mock()
    # landing page not served
    server.serve_path.return_value = (SERVED_REQUEST, ["harness"])
    result = runner.run([], ServerMap(), testcase)
    assert result.status == RunResult.ERROR
    assert result.served
    assert target.close.call_count == 1

def test_runner_03(mocker):
    """test reporting timeout"""
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)
    serv_files = ["a.bin", "/another/file.bin"]
    server.serve_path.return_value = (SERVED_TIMEOUT, serv_files)
    runner = Runner(server, target)
    target.detect_failure.return_value = target.RESULT_FAILURE
    result = runner.run([], ServerMap(), mocker.Mock(spec=TestCase, landing_page="x", optional=[]))
    assert result.status == RunResult.FAILED
    assert result.served == serv_files
    assert result.timeout

def test_runner_04(mocker):
    """test reporting failures"""
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)
    serv_files = ["file.bin"]
    server.serve_path.return_value = (SERVED_REQUEST, serv_files)
    testcase = mocker.Mock(spec=TestCase, landing_page=serv_files[0], optional=[])
    runner = Runner(server, target)
    # test FAILURE
    target.detect_failure.return_value = target.RESULT_FAILURE
    result = runner.run([], ServerMap(), testcase)
    assert result.status == RunResult.FAILED
    assert result.served == serv_files
    assert not result.timeout
    # test IGNORED
    target.detect_failure.return_value = target.RESULT_IGNORED
    result = runner.run([], ServerMap(), testcase)
    assert result.status == RunResult.IGNORED
    assert result.served == serv_files
    assert not result.timeout
    # failure before serving landing page
    server.serve_path.return_value = (SERVED_REQUEST, ["harness"])
    target.detect_failure.return_value = target.RESULT_FAILURE
    result = runner.run([], ServerMap(), testcase)
    assert result.status == RunResult.FAILED
    assert result.served
    assert not result.timeout

def test_runner_05(mocker):
    """test Runner() with idle checking"""
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)
    target.detect_failure.return_value = target.RESULT_NONE
    serv_files = ["/fake/file", "/another/file.bin"]
    server.serve_path.return_value = (SERVED_REQUEST, serv_files)
    runner = Runner(server, target, idle_threshold=0.01, idle_delay=0.01)
    assert runner._idle is not None
    result = runner.run([], ServerMap(), mocker.Mock(spec=TestCase, landing_page=serv_files[0], optional=[]))
    assert result.status == RunResult.COMPLETE
    assert target.close.call_count == 0

def test_runner_06(mocker):
    """test Runner._keep_waiting()"""
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)

    target.monitor.is_healthy.return_value = True
    runner = Runner(server, target)
    assert runner._keep_waiting()

    target.monitor.is_healthy.return_value = False
    assert not runner._keep_waiting()

    runner._idle = mocker.Mock(spec=_IdleChecker)
    runner._idle.is_idle.return_value = False
    target.monitor.is_healthy.return_value = True
    assert runner._keep_waiting()

    runner._idle.is_idle.return_value = True
    target.monitor.is_healthy.return_value = True
    assert not runner._keep_waiting()

    runner._idle.is_idle.return_value = False
    target.monitor.is_healthy.return_value = False
    assert not runner._keep_waiting()

def test_runner_07():
    """test Runner.location()"""
    result = Runner.location("a.html", 34567)
    assert result == "http://127.0.0.1:34567/a.html"
    result = Runner.location("/a.html", 34567)
    assert result == "http://127.0.0.1:34567/a.html"
    result = Runner.location("a.html", 34567, close_after=10)
    assert result == "http://127.0.0.1:34567/a.html?close_after=10"
    result = Runner.location("a.html", 34567, close_after=10, forced_close=False)
    assert result == "http://127.0.0.1:34567/a.html?close_after=10&forced_close=0"
    result = Runner.location("a.html", 34567, forced_close=False)
    assert result == "http://127.0.0.1:34567/a.html?forced_close=0"
    result = Runner.location("a.html", 9999, close_after=10, forced_close=False, timeout=60)
    assert result == "http://127.0.0.1:9999/a.html?close_after=10&forced_close=0&timeout=60000"

def test_runner_08(mocker):
    """test Runner.launch()"""
    server = mocker.Mock(spec=Sapphire, port=0x1337)
    target = mocker.Mock(spec=Target, launch_timeout=30)

    runner = Runner(server, target)
    runner.launch("http://a/")
    assert target.launch.call_count == 1
    target.reset_mock()

    target.launch.side_effect = TargetLaunchError("test", mocker.Mock(spec=Report))
    with raises(TargetLaunchError, match="test"):
        runner.launch("http://a/")
    assert target.launch.call_count == 1
    target.reset_mock()

    target.launch.side_effect = TargetLaunchTimeout
    with raises(TargetLaunchTimeout):
        runner.launch("http://a/", max_retries=3)
    assert target.launch.call_count == 3

def test_runner_09(mocker, tmp_path):
    """test Runner.run() adding includes to testcase"""
    server = mocker.Mock(spec=Sapphire)
    target = mocker.Mock(spec=Target)
    target.detect_failure.return_value = target.RESULT_NONE
    runner = Runner(server, target)
    # create test files
    inc_path1 = (tmp_path / "include")
    inc_path1.mkdir()
    inc1 = (inc_path1 / "inc_file.bin")
    inc1.write_bytes(b"a")
    (inc_path1 / "nested").mkdir()
    inc2 = (inc_path1 /  "nested" / "nested_inc.bin")
    inc2.write_bytes(b"a")
    inc_path2 = (tmp_path / "include2")
    inc_path2.mkdir()
    inc3 = (inc_path2 / "inc_file3.txt")
    inc3.write_bytes(b"a")
    # build server map
    smap = ServerMap()
    smap.set_include("/", str(inc_path1))
    smap.set_include("/test", str(inc_path2))
    serv_files = ["a.b", str(inc1), str(inc2), str(inc3)]
    server.serve_path.return_value = (SERVED_ALL, serv_files)
    with TestCase("a.b", "x", "x") as tcase:
        result = runner.run([], smap, tcase)
        assert result.status == RunResult.COMPLETE
        assert "inc_file.bin" in tcase._existing_paths
        assert pathjoin("nested", "nested_inc.bin") in tcase._existing_paths
        assert pathjoin("test", "inc_file3.txt") in tcase._existing_paths

def test_idle_check_01(mocker):
    """test simple _IdleChecker"""
    fake_time = mocker.patch("grizzly.common.runner.time", autospec=True)
    ichk = _IdleChecker(mocker.Mock(), 95, 10, poll_delay=1)
    assert ichk._threshold == 95
    assert ichk._init_delay == 10
    assert ichk._poll_delay == 1
    assert ichk._next_poll is None
    fake_time.return_value = 0
    ichk.schedule_poll(initial=True)
    assert ichk._next_poll == 10
    ichk.schedule_poll()
    assert ichk._next_poll == 1

def test_idle_check_02(mocker):
    """test _IdleChecker.is_idle()"""
    fake_time = mocker.patch("grizzly.common.runner.time", autospec=True)
    callbk = mocker.Mock()
    callbk.return_value = False
    ichk = _IdleChecker(callbk, 99, 10, poll_delay=1)
    fake_time.return_value = 0
    ichk.schedule_poll()
    # early check
    assert not ichk.is_idle()
    assert callbk.call_count == 0
    # not idle
    fake_time.return_value = 10
    assert not ichk.is_idle()
    assert ichk._next_poll == 11
    assert callbk.call_count == 1
    # idle
    callbk.return_value = True
    fake_time.return_value = ichk._next_poll
    assert ichk.is_idle()
    assert callbk.call_count == 2
