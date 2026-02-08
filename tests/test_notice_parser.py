import pytest
import datetime
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
        "expected": ([datetime.date(2026,1,1), datetime.date(2026,7,13), datetime.date(2026,5,4), datetime.date(2026,12,28)], [datetime.date(2026,12,26)])
    },
    {
        "input": """
        BY THE KING A PROCLAMATION APPOINTING MONDAY, 15TH JUNE 2026, AS A BANK HOLIDAY IN SCOTLAND CHARLES R.
        Whereas, to mark the achievement of Scotland’s men’s football team competing at the FIFA World Cup for the first time in 28 years, We consider it desirable that Monday, the fifteenth day of June in the year 2026 should be a bank holiday in Scotland.

        Now, therefore, We, in pursuance of section 1(3) of the Banking and Financial Dealings Act 1971, do hereby appoint Monday, the fifteenth day of June in the year 2026 to be a bank holiday in Scotland.

        Given at Our Court at Buckingham Palace this third day of February in the year of our Lord two thousand and twenty six in the fourth year of Our Reign.

        GOD SAVE THE KING
        """,
        "expected": ([datetime.date(2026,6,15)], [])
    }
]

@pytest.mark.parametrize("test_case", NOTICE_TESTS)
def test_notice_parser(test_case):
    input_text = test_case["input"]
    expected_bhs, expected_not_bhs = [set(l) for l in test_case["expected"]]

    parsed_bhs, parsed_not_bhs = [set(l) for l in notice_parser.parse_notice(input_text)]

    assert parsed_bhs == expected_bhs, f"Expected dates {expected_bhs} but got {parsed_bhs}"
    assert parsed_not_bhs == expected_not_bhs, f"Expected holidays {expected_not_bhs} but got {parsed_not_bhs}"
