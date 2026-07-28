import datetime

import pytest
import urllib3

from src import notice_parser

NOTICE_TESTS = [
    {
        "input": """
        BY THE KING A PROCLAMATION APPOINTING THURSDAY 1ST JANUARY 2026, MONDAY 4TH MAY 2026 AND APPOINTING MONDAY 28TH DECEMBER 2026 IN PLACE OF SATURDAY 26TH DECEMBER 2026 AS BANK HOLIDAYS IN ENGLAND, WALES AND NORTHERN IRELAND AND APPOINTING MONDAY 13TH JULY 2026 AS A BANK HOLIDAY IN NORTHERN IRELAND CHARLES R.
        Whereas, We consider it desirable that Thursday the first day of January and Monday the fourth day of May in the year 2026 should be bank holidays in England, Wales and Northern Ireland:

        And whereas, it appears to Us that it is inexpedient that Saturday the twenty-sixth day of December in the year 2026 should be a bank holiday in England, Wales and Northern Ireland and We consider it desirable that Monday the twenty-eighth day of December in the year 2026 should be appointed a bank holiday in England, Wales and Northern Ireland in place of it:

        And whereas, We consider it desirable that Monday the thirteenth day of July in the year 2026 should be a bank holiday in Northern Ireland:

        Now, therefore, We in pursuance of sections 1(2) and 1(3) of the Banking and Financial Dealings Act 1971, do hereby appoint Thursday the first day of January, Monday the fourth day of May and Monday the twenty-eighth day of December in the year 2026, in place of Saturday the twenty-sixth day of December in the year 2026 to be bank holidays in England, Wales and Northern Ireland and appoint Monday the thirteenth day of July in the year 2026 to be a bank holiday in Northern Ireland.

        Given at Our Court at Buckingham Palace, this ninth day of July in the year of our Lord two thousand and twenty-five in the third year of Our Reign.

        GOD SAVE THE KING
        """,
        "expected": (
            [
                datetime.date(2026, 1, 1),
                datetime.date(2026, 7, 13),
                datetime.date(2026, 5, 4),
                datetime.date(2026, 12, 28),
            ],
            [datetime.date(2026, 12, 26)],
        ),
    },
    {
        "input": """
        BY THE KING A PROCLAMATION APPOINTING MONDAY, 15TH JUNE 2026, AS A BANK HOLIDAY IN SCOTLAND CHARLES R.
        Whereas, to mark the achievement of Scotland’s men’s football team competing at the FIFA World Cup for the first time in 28 years, We consider it desirable that Monday, the fifteenth day of June in the year 2026 should be a bank holiday in Scotland.

        Now, therefore, We, in pursuance of section 1(3) of the Banking and Financial Dealings Act 1971, do hereby appoint Monday, the fifteenth day of June in the year 2026 to be a bank holiday in Scotland.

        Given at Our Court at Buckingham Palace this third day of February in the year of our Lord two thousand and twenty six in the fourth year of Our Reign.

        GOD SAVE THE KING
        """,
        "expected": ([datetime.date(2026, 6, 15)], []),
    },
    {
        "input": """
        BY THE KING A PROCLAMATION APPOINTING MONDAY, 28TH DECEMBER 2026, IN THE PLACE OF SATURDAY, 26TH DECEMBER 2026, APPOINTING MONDAY, 4TH JANUARY 2027 IN THE PLACE OF SATURDAY, 2ND JANUARY 2027, AND MONDAY 31ST MAY 2027, AS BANK HOLIDAYS IN SCOTLAND CHARLES R.
        Now, therefore, We, in pursuance of section 1(3) of the Banking and Financial Dealings Act 1971, do hereby appoint Monday, the twenty-eighth day of December in the year 2026, Monday, the fourth day of January 2027 and Monday the thirty-first day of May in the year 2027 to be bank holidays in Scotland.

        And whereas it appears to Us that it is inexpedient that Saturday, the twenty-sixth day of December in the year 2026 should be a bank holiday in Scotland and We consider it desirable that Monday, the twenty-eighth day of December in the year 2026 should be appointed a bank holiday in Scotland in place of it:

        And whereas it appears to Us that it is inexpedient that Saturday the second day of January in the year 2027 should be a bank holiday in Scotland and We consider it desirable that Monday, the fourth day of January in the year 2027 should be appointed a bank holiday in Scotland in place of it:

        We consider it desirable that Monday, the thirty-first day of May in the year 2027 should be appointed a bank holiday in Scotland.

        Now, therefore, We, in pursuance of section 1(3) of the Banking and Financial Dealings Act 1971, do hereby appoint Monday, the twenty-eighth day of December in the year 2026, Monday, the fourth day of January in the year 2027 and Monday, the thirty-first day of May in the year 2027 to be bank holidays in Scotland.

        Given at Our Court at Buckingham Palace this eighth day of July in the year of our Lord two thousand and twenty six in the fourth year of Our Reign.

        GOD SAVE THE KING
        """,
        "expected": (
            [
                datetime.date(2026, 12, 28),
                datetime.date(2027, 1, 4),
                datetime.date(2027, 5, 31),
            ],
            [datetime.date(2026, 12, 26), datetime.date(2027, 1, 2)],
        ),
    },
]


@pytest.mark.parametrize("test_case", NOTICE_TESTS)
def test_notice_parser(test_case):
    input_text = test_case["input"]
    expected_bhs, expected_not_bhs = [set(l) for l in test_case["expected"]]

    parsed_bhs, parsed_not_bhs = [
        set(l) for l in notice_parser.parse_notice(input_text)
    ]

    assert parsed_bhs == expected_bhs, (
        f"Expected dates {expected_bhs} but got {parsed_bhs}"
    )
    assert parsed_not_bhs == expected_not_bhs, (
        f"Expected holidays {expected_not_bhs} but got {parsed_not_bhs}"
    )


def test_lambda_handler_does_not_reuse_results_between_invocations(monkeypatch):
    import importlib
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src"))
    lambda_function = importlib.import_module("lambda_function")

    class FakeS3:
        def __init__(self):
            self.puts = []

        def put_object(self, **kwargs):
            self.puts.append(kwargs)

    s3 = FakeS3()
    monkeypatch.setattr(
        lambda_function.boto3,
        "client",
        lambda service: s3 if service == "s3" else object(),
    )
    monkeypatch.setattr(lambda_function, "S3_BUCKET", "test-bucket")
    monkeypatch.setattr(
        lambda_function,
        "get_notice_text",
        lambda http, notice_id: "notice text",
    )
    monkeypatch.setattr(
        lambda_function,
        "parse_notice",
        lambda text: ([datetime.date(2026, 12, 28)], []),
    )
    monkeypatch.setattr(
        lambda_function.urllib3,
        "PoolManager",
        lambda **kwargs: object(),
    )

    fetch_count = 0

    def fetch_one_notice_per_invocation(http, gazette, query, callback):
        nonlocal fetch_count
        fetch_count += 1
        if fetch_count in (1, 4):
            callback({"id": "https://www.thegazette.co.uk/id/notice/5160659"})

    monkeypatch.setattr(
        lambda_function, "fetch_all_notices", fetch_one_notice_per_invocation
    )

    first = lambda_function.lambda_handler({}, {})
    second = lambda_function.lambda_handler({}, {})

    assert (
        first
        == second
        == {
            "bank_holidays": {
                "https://www.thegazette.co.uk/id/notice/5160659": ["2026-12-28"]
            },
            "not_bank_holidays": {},
        }
    )
    assert len(s3.puts) == 4


def test_notice_5160659_parser_regression():
    input_text = """
        BY THE KING A PROCLAMATION APPOINTING MONDAY, 28TH DECEMBER 2026, IN THE PLACE OF SATURDAY, 26TH DECEMBER 2026, APPOINTING MONDAY, 4TH JANUARY 2027 IN THE PLACE OF SATURDAY, 2ND JANUARY 2027, AND MONDAY 31ST MAY 2027, AS BANK HOLIDAYS IN SCOTLAND CHARLES R.Now, therefore, We, in pursuance of section 1(3) of the Banking and Financial Dealings Act 1971, do hereby appoint Monday, the twenty-eighth day of December in the year 2026, Monday, the fourth day of January 2027 and Monday the thirty-first day of May in the year 2027 to be bank holidays in Scotland.
        And whereas it appears to Us that it is inexpedient that Saturday, the twenty-sixth day of December in the year 2026 should be a bank holiday in Scotland and We consider it desirable that Monday, the twenty-eighth day of December in the year 2026 should be appointed a bank holiday in Scotland in place of it:
    """

    bank_holidays, not_bank_holidays = notice_parser.parse_notice(input_text)

    assert set(bank_holidays) == {
        datetime.date(2026, 12, 28),
        datetime.date(2027, 1, 4),
        datetime.date(2027, 5, 31),
    }
    assert set(not_bank_holidays) == {
        datetime.date(2026, 12, 26),
        datetime.date(2027, 1, 2),
    }


def test_process_notice_logs_failed_notice_id(monkeypatch, caplog):
    import importlib
    import logging
    from pathlib import Path

    monkeypatch.syspath_prepend(str(Path(__file__).parents[1] / "src"))
    lambda_function = importlib.import_module("lambda_function")
    notice_id = "https://www.thegazette.co.uk/id/notice/5160659"

    def fail_to_fetch(http, requested_notice_id):
        raise ValueError("test fetch failure")

    monkeypatch.setattr(lambda_function, "get_notice_text", fail_to_fetch)
    monkeypatch.setattr(lambda_function, "SNS_TOPIC", None)
    caplog.set_level(logging.ERROR)

    with pytest.raises(ValueError, match="test fetch failure"):
        lambda_function.process_notice(
            object(), urllib3.PoolManager(), {"id": notice_id}
        )

    assert f"Failed to process notice '{notice_id}' (ValueError)" in caplog.text
