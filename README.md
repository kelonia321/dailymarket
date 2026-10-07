# 미국 금리·시장 안정도 대시보드

매주 화~토 오전 7시(KST)에 GitHub Actions가 FRED와 Yahoo Finance의 무료 데이터를 받아 대시보드를 갱신합니다.

- 대시보드 주소: https://kelonia321.github.io/dailymarket/
- 날짜별 기록: `docs/archive/` 폴더
- 점수 이력: `data/history.csv`

## 구성

| 파일 | 역할 |
|---|---|
| `config.json` | 지표, 가중치, 점수 기준 |
| `main.py` | 매일 실행되는 진입점 |
| `src/fetch.py` | FRED·Yahoo 데이터 수집 (실패 시 대체 소스) |
| `src/score.py` | 지표별·종합 점수 산출 |
| `src/regime.py`, `src/summary.py` | 국면 판정과 3줄 요약 |
| `src/render.py` | HTML 대시보드 생성 |
| `.github/workflows/daily.yml` | 매일 자동 실행 설정 |
| `tests/` | 자동 테스트 (실행 때마다 먼저 통과해야 대시보드 갱신) |

## 자주 묻는 상황

- 오늘 대시보드가 안 바뀌었다: Actions 탭에서 최근 실행 결과를 확인합니다. 빨간 X는 실패이며, 기존 대시보드는 그대로 유지됩니다. "Run workflow"로 다시 실행할 수 있습니다.
- 자동 실행이 멈췄다: Actions 탭 상단에 비활성화 안내가 보이면 "Enable workflow"를 누릅니다.
- 가중치를 바꾸고 싶다: `config.json`에서 `groups`의 `weight` 값을 수정합니다 (연필 아이콘으로 웹에서 바로 편집 가능).

본 대시보드는 분석 보조 목적이며 투자 권유가 아닙니다.
