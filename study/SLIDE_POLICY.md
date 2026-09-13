# DeepPersona 스터디 덱 — 로컬 슬라이드 정책

전거(중앙 master): `~/tools/latex-autobuild/docs/slide-content-policy.md`, `LATEX_정책.md`.
이 파일은 **이 프로젝트 고유 규칙 + 상속 원칙 중 특히 중요한 것 + 실험 로그**를 담는다(governance §0).

## ① 이 프로젝트 고유 규칙

- **테마/언어**: `metropolis-kr`(XeLaTeX + kotex), **한국어 단일**(사용자 2026-09-13 선택). 필요 시 특정 모듈만 EN 페어.
- **폰트(이 랩탑)**: 한글 `Apple SD Gothic Neo`, 코드 `D2Coding`. Fira 미설치 → metropolis는 라틴을 폴백(무해).
- **팔레트**: accent(teal `#0E7C7B`), navy(kaistblue `#004191`), `\alert`=orange `#F97316`, 블록=청회색 `#EDF1F6`.
- **저작권**: 논문 원본 도표/PDF는 로컬 빌드용으로만 삽입하고 **커밋 금지**(`\IfFileExists`로 감싸 자산 없어도 빌드되게). 지금까지 모듈은 전부 **직접 재작도(TikZ)** 만 사용.
- **출처 표기**: 표지·각 도식에 논문 Fig/Eq 번호를 `\srcnote`로 명기.

## ② 상속 원칙 중 이 프로젝트에서 특히 중요한 것

- **코드 설명 필수 형식**: 코드블록(발췌) + "각 줄이 무엇을·왜". 스터디 핵심이 코드 재현이므로 모든 코드 모듈에 적용.
- **수식 3단**: 직관(`\intu`) → 기호 전부 정의 → 세부. Eq(1)(2)에서 이미 적용.
- **매핑 방향 강조**: "값→슬롯"이 아니라 "인물→슬롯 발견" — 학습자가 가장 자주 오해하는 지점(study.md §8과 연결).
- **넘침 관리**: `Overfull \vbox`는 결함. 렌더 PNG로 잘림 눈 확인. `\maketitle`/`standout`의 소량 넘침은 metropolis 구조적이라 예외.

## ③ 실험 로그

| 항목 | 상태 | 근거 |
|---|---|---|
| 베이스 폰트 10pt(밀도 우선) | 검증됨 | 11pt에서 다수 프레임 10~18pt 넘침 → 10pt로 대부분 해소(모듈 01) |
| `latexmk -xelatex` 최초 실패 후 `-C` 클린하면 정상 | 검증됨 | 잘린 `.xdv` 잔재가 rerun에서 rc=1 유발. 클린 후 exit 0 |
| `\pc{}` 인라인 코드 배지(글자만) | 검증됨 | `\colorbox` 대신 TikZ node(inner ysep=1pt)로 행간 오염 방지(정책 §2.7) |
| `&` 는 섹션/본문에서 `\&` 로 이스케이프 | 검증됨 | `\section{... & ...}`가 Misplaced alignment tab로 빌드 중단 |
| `\lead` 아래 여백은 **1.15em 유지**(정책 §4.1) | 확정 | 넘침 잡겠다고 0.6em로 줄인 건 오류(사용자 지적). 넘침은 배너가 아니라 본문을 줄여 해결 |
| TikZ node에 `\\` 쓰면 style에 `align=center` 필수 | 검증됨 | 없으면 "Not allowed in LR mode"로 빌드 중단 |
| 원본 논문 그림 삽입 워크플로 | 검증됨 | `pdftoppm -r300`→PIL 크롭→`figs/`(gitignore)→`\origfig`(=`\IfFileExists`). Fig2(모듈01)·Fig3 선버스트(모듈02) |
| 넓은 가로 그림은 `height`를 작게(0.46\textheight) | 검증됨 | 가로 넓은 Fig2를 height 0.62로 주면 폭·높이 동시 초과 |
| `&`는 **프레임/섹션 제목에서도** `\&` | 검증됨 | `\begin{frame}{... & ...}`도 Misplaced alignment tab로 중단(모듈05) |
| 입문 튜토리얼(private) `gh api ... contents`로 취득 | 검증됨 | raw URL 404. `gh api repos/.../contents/<path>` → base64 디코드. references.bib에 `deeppersona_tutorial` 등재 |
| 코드 학습 모듈 = 코드블록(listings)+줄별 불릿 | 확정 패턴 | 한글은 코드 밖 불릿에, 코드블록은 영문/ASCII 위주로 두어 listings-한글 이슈 회피 |

## ④ 승격(promote) 대기/완료

- (대기) "metropolis 최초 빌드 rc=1 → `-C` 클린" 레시피를 중앙 CLAUDE.md 함정 목록에 올릴지 검토.
- (대기) 코드 학습교재 전용 패턴(코드블록+줄별 표) 템플릿화 여부.
