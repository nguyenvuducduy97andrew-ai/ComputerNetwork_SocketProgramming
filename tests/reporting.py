"""Định dạng kết quả kiểm thử nhất quán bằng tiếng Việt."""

from __future__ import annotations

import unittest


def print_test_suite(title: str) -> None:
    print(f"\n=== KIỂM THỬ {title.upper()} ===")


def print_test_step(message: str) -> None:
    print(f"[+] {message}")


def print_test_result(message: str) -> None:
    print(f"[KẾT QUẢ] ĐẠT: {message}")


class VietnameseTestCase(unittest.TestCase):
    """TestCase in mô tả và kết quả theo một bố cục thống nhất."""

    suite_title = "CHỨC NĂNG HỆ THỐNG"

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        print_test_suite(cls.suite_title)

    def run(self, result: unittest.TestResult | None = None):
        description = self.shortDescription() or self._testMethodName
        print_test_step(description)

        failures_before = len(result.failures) if result is not None else 0
        errors_before = len(result.errors) if result is not None else 0
        skipped_before = len(result.skipped) if result is not None else 0

        outcome = super().run(result)

        if result is not None:
            passed = (
                len(result.failures) == failures_before
                and len(result.errors) == errors_before
                and len(result.skipped) == skipped_before
            )
            if passed:
                print_test_result(description)

        return outcome
