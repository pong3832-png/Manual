from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = PROJECT_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from quantum_trainer.kind_universe import normalize_kind_corp_list, parse_kind_corp_list_html


def test_parse_kind_corp_list_html_extracts_table_rows() -> None:
    html = """
    <table>
      <tr>
        <th>\ud68c\uc0ac\uba85</th><th>\uc2dc\uc7a5\uad6c\ubd84</th>
        <th>\uc885\ubaa9\ucf54\ub4dc</th><th>\uc5c5\uc885</th>
      </tr>
      <tr>
        <td>Samsung Electronics</td><td>\ucf54\uc2a4\ud53c</td>
        <td>005930</td><td>Semiconductors</td>
      </tr>
    </table>
    """

    parsed = parse_kind_corp_list_html(html)

    assert parsed.columns.tolist() == ["\ud68c\uc0ac\uba85", "\uc2dc\uc7a5\uad6c\ubd84", "\uc885\ubaa9\ucf54\ub4dc", "\uc5c5\uc885"]
    assert parsed.loc[0, "\ud68c\uc0ac\uba85"] == "Samsung Electronics"
    assert parsed.loc[0, "\uc885\ubaa9\ucf54\ub4dc"] == "005930"


def test_normalize_kind_corp_list_maps_kospi_and_kosdaq_and_excludes_konex() -> None:
    parsed = parse_kind_corp_list_html(
        """
        <table>
          <tr>
            <th>\ud68c\uc0ac\uba85</th><th>\uc2dc\uc7a5\uad6c\ubd84</th>
            <th>\uc885\ubaa9\ucf54\ub4dc</th><th>\uc5c5\uc885</th>
          </tr>
          <tr><td>Samsung Electronics</td><td>\ucf54\uc2a4\ud53c</td><td>005930</td><td>Semiconductors</td></tr>
          <tr><td>Celltrion Healthcare</td><td>\ucf54\uc2a4\ub2e5</td><td>091990</td><td>Biotech</td></tr>
          <tr><td>Konex Sample</td><td>\ucf54\ub125\uc2a4</td><td>123456</td><td>Sample</td></tr>
        </table>
        """
    )

    universe = normalize_kind_corp_list(parsed)

    assert universe["symbol"].tolist() == ["005930.KS", "091990.KQ"]
    assert universe["market"].tolist() == ["KOSPI", "KOSDAQ"]
    assert universe["sector"].tolist() == ["Semiconductors", "Biotech"]
    assert universe["security_type"].tolist() == ["STOCK", "STOCK"]


def test_normalize_kind_corp_list_maps_kind_yuga_market_to_kospi() -> None:
    parsed = parse_kind_corp_list_html(
        """
        <table>
          <tr>
            <th>\ud68c\uc0ac\uba85</th><th>\uc2dc\uc7a5\uad6c\ubd84</th>
            <th>\uc885\ubaa9\ucf54\ub4dc</th><th>\uc5c5\uc885</th>
          </tr>
          <tr><td>Samsung Electronics</td><td>\uc720\uac00</td><td>005930</td><td>Semiconductors</td></tr>
        </table>
        """
    )

    universe = normalize_kind_corp_list(parsed)

    assert universe.loc[0, "symbol"] == "005930.KS"
    assert universe.loc[0, "market"] == "KOSPI"
