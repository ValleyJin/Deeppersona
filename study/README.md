# DeepPersona 코드 학습교재 (슬라이드)

이 폴더는 DeepPersona 코드를 **이해하고 그대로 재현**하기 위한 학습용 슬라이드 덱 모음이다.
각 서브폴더가 하나의 자립적인 스터디 덱(`main.tex` → `main.pdf`)이다.

- 원저 논문: Wang et al., *DeepPersona* (arXiv:2511.07338) — 루트의 PDF 참조.
- 상위 학습 노트: 루트의 `study.md`(질의응답식 정리)와 상호 보완한다.
- 도구: `latex-autobuild`의 `metropolis-kr` 테마(XeLaTeX + kotex), 한국어.

## 모듈 목록

| # | 폴더 | 주제 | 코드/논문 대응 | 상태 |
|---|---|---|---|---|
| 01 | `01_overview/` | 큰 그림 — 문제·2단계 파이프라인·코드↔논문 지도·핵심 수식 | 전체 · 논문 §1–§3 | ✅ |
| 02 | `02_taxonomy/` | 속성 트리(Stage 1)와 데이터 파일 구조 | `process_attributes/`, `data/*.json` · §3.1 | ✅ |
| 03 | `03_based_data/` | 시드/앵커 코어 생성 | `based_data.py` · §3.2 | ✅ |
| 04 | `04_select_attributes/` | 임베딩 + 5:3:2 슬롯 선택 | `select_attributes.py` · §3.2 | ✅ |
| 05 | `05_generate_profile/` | 깊이우선 값 채우기 + Summary | `generate_profile.py` · §3.2 | ✅ |
| 06 | `06_run_reproduce/` | 실행·재현·스크립트 | `scripts/`, `.env` | ✅ |

**교재 완성** — 6개 모듈 전부 빌드 검증(`latexmk -xelatex`, exit 0). 총 110쪽.

## 참고 자료

- 입문 튜토리얼(상보적): [ValleyJin/Tutorial-Builder — Deeppersona](https://github.com/ValleyJin/Tutorial-Builder/blob/main/output/Deeppersona/index.md) — 5장(비유 중심). 본 교재는 코드 밀착 심화. 각 모듈 `references.bib`에 등재(`deeppersona_tutorial`).

## 빌드

각 폴더에서:

```bash
cd 01_overview
make            # = latexmk -xelatex main.tex  (한글은 XeLaTeX 필수)
```

- `main.pdf`가 산출물. 빌드 부산물(`.aux/.log/.xdv/...`)은 루트 `.gitignore`로 제외됨.
- 한글 폰트: `Apple SD Gothic Neo`, 코드 고정폭: `D2Coding`(이 랩탑 기준).
  다른 환경이면 `main.tex` 상단 `\setmainhangulfont`/`\setmonofont`를 설치 폰트로 교체.

## 작성 정책 (요약)

전거: `~/tools/latex-autobuild/docs/slide-content-policy.md` + `LATEX_정책.md`. 이 프로젝트 적용 규칙은 `SLIDE_POLICY.md` 참조.

- 수식은 **직관 → 기호(전부 정의) → 세부** 순(`\intu` 배너).
- **코드 설명은 코드블록 + 줄별 "무엇을·왜"** 를 반드시 병기.
- 인라인 코드 배지는 글자만 감싸는 `\pc{}`(TikZ) 사용.
- 도식은 여백을 채울 만큼 크게, 단 프레임을 넘겨 잘리지 않게(Overfull \vbox 최소화).
- 한국어 단일 언어(사용자 선택). 필요 시 특정 모듈만 EN 페어 추가.
