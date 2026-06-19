import csv
import tempfile
import unittest
import zipfile
from pathlib import Path

from naver_product_output import save_detail_review_outputs
from naver_product_parser import ProductSummary, ReviewItem


class DetailReviewOutputTest(unittest.TestCase):
    def test_save_detail_review_outputs_writes_txt_csv_and_xlsx(self):
        summary = ProductSummary(
            product_name="리얼베리어 세라마이드 클렌징 밀크 200ml, 1개",
            rating=4.86,
            recent_six_month_rating=4.8,
            price_krw=17500,
            review_count=836,
        )
        reviews = [
            ReviewItem(
                review_id="4981125260",
                rating=5,
                content="민감성 피부도 안심하고 쓸 수 있는 순한 클렌저입니다.",
            ),
            ReviewItem(
                review_id="4984044821",
                rating=4,
                content="향은 은은하고 세안 후 당김이 적어요.",
            ),
        ]

        with tempfile.TemporaryDirectory() as temp_dir:
            paths = save_detail_review_outputs(
                summary,
                reviews,
                base_dir=temp_dir,
                timestamp="2026-05-27-12-34-56",
            )

            self.assertTrue(Path(paths["txt"]).exists())
            self.assertTrue(Path(paths["csv"]).exists())
            self.assertTrue(Path(paths["xlsx"]).exists())
            self.assertIn("2026-05-27-12-34-56-리얼베리어", paths["output_dir"])

            txt = Path(paths["txt"]).read_text(encoding="utf-8")
            self.assertIn("번호\t개별 평점\t리뷰 내용", txt)
            self.assertIn("1\t5\t민감성 피부도 안심하고 쓸 수 있는 순한 클렌저입니다.", txt)
            self.assertNotIn("product_name", txt)
            self.assertNotIn("4981125260", txt)

            with Path(paths["csv"]).open("r", encoding="utf-8-sig", newline="") as csv_file:
                rows = list(csv.DictReader(csv_file))
            self.assertEqual(list(rows[0].keys()), ["번호", "개별 평점", "리뷰 내용"])
            self.assertEqual(rows[0]["번호"], "1")
            self.assertEqual(rows[0]["개별 평점"], "5")
            self.assertEqual(rows[0]["리뷰 내용"], "민감성 피부도 안심하고 쓸 수 있는 순한 클렌저입니다.")

            with zipfile.ZipFile(paths["xlsx"]) as workbook:
                self.assertIn("xl/worksheets/sheet1.xml", workbook.namelist())
                sheet_xml = workbook.read("xl/worksheets/sheet1.xml").decode("utf-8")
            self.assertIn("번호", sheet_xml)
            self.assertIn("개별 평점", sheet_xml)
            self.assertIn("리뷰 내용", sheet_xml)
            self.assertNotIn("4984044821", sheet_xml)
            self.assertIn("향은 은은하고 세안 후 당김이 적어요.", sheet_xml)


if __name__ == "__main__":
    unittest.main()
