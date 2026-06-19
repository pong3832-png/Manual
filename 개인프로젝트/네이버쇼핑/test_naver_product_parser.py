import unittest

from naver_product_parser import (
    REVIEW_ITEM_SELECTOR,
    REVIEW_LINK_SELECTOR,
    REVIEW_MORE_BUTTON_SELECTOR,
    parse_product_summary,
    parse_reviews,
)


PRODUCT_HTML = """
<html>
  <body>
    <div class="cy0UBkueTk _copyable">
      <h3 class="y67cdgB6Ve">리얼베리어 세라마이드 클렌징 밀크 200ml, 1개</h3>
    </div>
    <div class="cgWXbnzuxd">
      <span class="QDu1sxdjM6">4.86</span>
      <div class="i6jWy_bhvL">
        (<span id="tooltip_text_:r1:" role="button">최근 6개월 4.87</span>)
      </div>
    </div>
    <div class="hPxxcpW7TV ehZeGXTauk">
      <span class="blind">상품 가격</span>
      <span class="weP_mymkqG">17,500</span>
      <span class="imTYCu8Fi7">원</span>
    </div>
    <a href="#" class="cgWXbnzuxd faVe5_Gpsq _nlog_click"
       data-shp-area-id="rvmore">831건 리뷰</a>
  </body>
</html>
"""


REVIEWS_HTML = """
<html>
  <body>
    <ul>
      <li class="N9LWAcN4hj" id="REVIEW_ITEM_4981125260">
        <div class="F6N7Rr56mQ">
          <svg></svg>5
        </div>
        <div class="ibGaqMAxQ2 J2k3y9ViPd">
          <p class="Uv4T3VkhKU byx8QlYdnz" id="review_content_4981125260">
            민감성 피부도 안심하고 쓸 수 있는 순한 클렌저라는 느낌이 강하게 들었습니다.
          </p>
          <a href="#" class="VMyQHeqVPn" aria-labelledby="review_option_4981125260 review_content_4981125260">
            <div class="o9hXpI5EsJ">접기</div>
          </a>
        </div>
      </li>
      <li class="N9LWAcN4hj" id="REVIEW_ITEM_4984044821">
        <div class="F6N7Rr56mQ">
          <svg></svg>4
        </div>
        <div class="ibGaqMAxQ2 J2k3y9ViPd">
          <p class="Uv4T3VkhKU byx8QlYdnz" id="review_content_4984044821">
            향은 은은하고 세안 후 당김이 적어요.
            가격 대비 만족합니다.
          </p>
          <a href="#" class="VMyQHeqVPn" aria-labelledby="review_option_4984044821 review_content_4984044821">
            <div class="o9hXpI5EsJ">더보기</div>
          </a>
        </div>
      </li>
    </ul>
  </body>
</html>
"""


class ProductSummaryParserTest(unittest.TestCase):
    def test_parse_product_summary_extracts_first_stage_product_fields(self):
        summary = parse_product_summary(PRODUCT_HTML)

        self.assertEqual(summary.product_name, "리얼베리어 세라마이드 클렌징 밀크 200ml, 1개")
        self.assertEqual(summary.rating, 4.86)
        self.assertEqual(summary.recent_six_month_rating, 4.87)
        self.assertEqual(summary.price_krw, 17500)
        self.assertEqual(summary.review_count, 831)

    def test_review_link_selector_targets_review_more_link(self):
        self.assertIn("data-shp-area-id='rvmore'", REVIEW_LINK_SELECTOR)
        self.assertIn(".faVe5_Gpsq", REVIEW_LINK_SELECTOR)

    def test_recent_rating_normalizes_missing_decimal_point(self):
        html = PRODUCT_HTML.replace("최근 6개월 4.87", "최근 6개월 48")

        summary = parse_product_summary(html)

        self.assertEqual(summary.recent_six_month_rating, 4.8)


class ReviewParserTest(unittest.TestCase):
    def test_parse_reviews_extracts_review_id_rating_and_content(self):
        reviews = parse_reviews(REVIEWS_HTML)

        self.assertEqual(len(reviews), 2)
        self.assertEqual(reviews[0].review_id, "4981125260")
        self.assertEqual(reviews[0].rating, 5)
        self.assertEqual(
            reviews[0].content,
            "민감성 피부도 안심하고 쓸 수 있는 순한 클렌저라는 느낌이 강하게 들었습니다.",
        )
        self.assertEqual(reviews[1].review_id, "4984044821")
        self.assertEqual(reviews[1].rating, 4)
        self.assertEqual(reviews[1].content, "향은 은은하고 세안 후 당김이 적어요. 가격 대비 만족합니다.")

    def test_review_selectors_target_review_items_and_more_buttons(self):
        self.assertEqual(REVIEW_ITEM_SELECTOR, "li[id^='REVIEW_ITEM_']")
        self.assertIn("a.VMyQHeqVPn", REVIEW_MORE_BUTTON_SELECTOR)

    def test_parse_reviews_keeps_void_tags_from_leaking_button_text_into_content(self):
        html = """
        <li class="N9LWAcN4hj" id="REVIEW_ITEM_4981659991">
          <div class="F6N7Rr56mQ"><svg></svg>5</div>
          <p class="Uv4T3VkhKU byx8QlYdnz" id="review_content_4981659991">
            순하고 촉촉해요.<br>재구매 의사 있습니다.
          </p>
          <img src="review.jpg">
          <a href="#" class="VMyQHeqVPn" aria-labelledby="review_option_4981659991 review_content_4981659991">
            <div class="o9hXpI5EsJ">더보기</div>
          </a>
        </li>
        """

        reviews = parse_reviews(html)

        self.assertEqual(len(reviews), 1)
        self.assertEqual(reviews[0].content, "순하고 촉촉해요. 재구매 의사 있습니다.")


if __name__ == "__main__":
    unittest.main()
