# DeepPersona Study Notes

본 fork(`ValleyJin/Deeppersona`)에서 Claude와 함께 진행한 학습 세션 요약.
원본: [thzva/Deeppersona](https://github.com/thzva/Deeppersona) — arXiv:2511.07338

---

## 1. 환경 설정

### Q. 현재 pip install이 이루어졌는가? .venv 환경에서 설치하는 게 좋을 것 같다

- 시점 점검 결과: 어떤 pip 설치도 이루어지지 않음, `.venv`도 없음
- 시스템 Python: 3.14.5 — `sentence-transformers`/`torch` wheel 호환성 우려
- **선택: Python 3.11.15로 `.venv` 생성** (ML 패키지 호환성 가장 안정)

```bash
python3.11 -m venv .venv
.venv/bin/pip install --upgrade pip
.venv/bin/pip install openai sentence-transformers scikit-learn numpy tqdm geonamescache python-dotenv
```

설치된 주요 패키지:
- `openai` 2.40.0
- `sentence-transformers` 5.5.1 (`torch` 2.12.0)
- `scikit-learn` 1.9.0
- `numpy` 2.4.6
- `python-dotenv` 1.2.2

`.venv`는 `.gitignore`에 이미 포함되어 있어 자동 제외.

---

## 2. 시크릿 관리 (.env 도입)

### Q. .env를 만들어서 환경변수를 넣도록 관련 코드를 수정하라

**문제**: 5개 파일에 `OPENAI_API_KEY = "OPENAI_API_KEY"` 형태로 placeholder 하드코딩

**대응 패턴** (모든 파일 동일):
```python
import os
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("OPENAI_API_KEY is not set. Add it to .env (see .env.example).")
```

**파일**:
- `.env` (gitignored) — 실제 시크릿
- `.env.example` (커밋) — 템플릿
- 수정된 5개: `generate_user_profile/config.py`, `process_attributes/{check_leaves,extract_personalized_attributes,filter_personalized_attributes,merge_tree}.py`

`generate_user_profile/config.py`에서 `GEONAMES_USERNAME`도 같은 패턴으로 처리.

---

## 3. Git Remote 전략

### Q. 지금 git init이 된 상태인가?

이미 git repo, `origin`이 `thzva/Deeppersona` (원저자) 가리킴.

### Q. Remote는 아직 안 잡혀있지?

잡혀 있으나 본인 권한 없음. 옵션 3가지:
1. 읽기 전용 사용
2. 본인 fork로 origin 변경
3. **upstream/origin 분리** (표준 OSS workflow)

### Q. 그냥 빈 repo를 만들고 거기에 remote를 연결해도 되나

가능. 차이점:
| | Fork | 빈 repo |
|---|---|---|
| GitHub "forked from" 표시 | O | X |
| upstream PR 가능 | O | X |
| 완전한 독립 | X | O |

### Q. fork "forked from" 표시가 안 되면 저작권 문제는?

**법적 (MIT)**: GitHub UI는 법적 요구사항 아님. LICENSE 동봉 + copyright notice 보존이면 충분.

**그러나 발견된 문제**:
- 원본 repo가 README에서 MIT를 선언하지만 **LICENSE 파일 자체가 없음**
- 학술 코드(arXiv)에서는 인용(citation) > 라이선스 — 출처 표시 누락은 표절 우려

**학술적 권장**:
1. README 상단에 fork 출처 명시
2. LICENSE 파일 추가 (원저자 copyright 보존)
3. Citation 섹션 유지

### Q. 공식적으로 fork를 해서 하는 게 낫겠다.

선택. `gh` CLI로 fork 후 remote 정리:
```bash
git remote set-url origin https://github.com/ValleyJin/Deeppersona.git
git remote add upstream https://github.com/thzva/Deeppersona.git
```

**향후 upstream 동기화**:
```bash
git fetch upstream
git merge upstream/main
git push origin main
```

---

## 4. 코드 정리

### 4-1. 하드코딩 경로 제거

발견된 `/home/zhou/...` 경로 8군데. `Path(__file__).resolve().parent[.parent]` 패턴으로 repo-relative 해소.

| 파일:라인 | 원본 | 수정 |
|---|---|---|
| `select_attributes.py:58` | `/home/zhou/.../large_attributes.json` | `_REPO_ROOT / "data" / "large_attributes.json"` |
| `select_attributes.py:61` | `/home/zhou/.../attribute_embeddings.pkl` | `_REPO_ROOT / "data" / "attribute_embeddings.pkl"` |
| `select_attributes.py:869` | 출력 디렉토리 | `_REPO_ROOT / "output"` |
| `generate_profile.py:686` | 출력 디렉토리 | `project_root / "output"` |
| `extract_personalized_attributes.py:25` | template.json | `Path(__file__).parent / "template.json"` |
| `filter_personalized_attributes.py:55` | template.json | 동일 |
| `check_leaves.py:367` | sample input | `repo_root / "data" / "attributes_merged.json"` |

### 4-2. Import-time 부수효과 버그

`select_attributes.py` 최하단:
```python
# 원본 (line 909 주석은 "import 전용"이라 명시)
user_profile = generate_user_profile()
selected_paths = get_selected_attributes(user_profile)
save_results(user_profile, selected_paths)
```

→ import만 해도 API 호출 시작. `if __name__ == "__main__":` guard로 묶음.

---

## 5. 동작 테스트 (Smoke Test)

### 테스트 스크립트 (`scripts/test_single_profile.py`)

`generate_single_profile()`을 attribute_count=100으로 1회 호출.

**결과**:
- API key 정상 로드 O
- 모듈 import 성공 O
- End-to-end pipeline 23.5초 만에 완료 O
- ⚠ **출력 profile이 1.9KB** (정상 시 ~1MB) — 거의 비어있음

**원인**: 로그에서 발견
```
ERROR - 加载嵌入向量时出错: pickle data was truncated
WARNING - 没有可用的向量数据库或向量搜索失败，返回空列表
```

→ `data/attribute_embeddings.pkl`이 손상되어 attribute selection이 모두 실패.

---

## 6. Pickle 손상 분석

### 6-1. 손상 사실 확인
- Local: 6,815,744 bytes (정확히 6.5 MiB)
- Upstream (`thzva/Deeppersona`): 동일하게 6,815,744 bytes
- 둘 다 `pickle.load()` 실행 시 `pickle data was truncated`로 실패
- **원본 repo 자체의 결함** — 전송 오류 아님

### 6-2. 손상 위치 forensic 분석

```python
pickletools.genops(data)
# ValueError: expected 28225536 bytes in a bytes4, but only 6676409 remain
```

→ numpy 배열 직렬화 도중 잘림. 원본 사이즈는 28,225,536 bytes여야 함 (76% 손실).

### 6-3. 모델 식별 (산수로 역추론)

- `28,225,536 bytes ÷ 8(float64) ÷ 1,536(dim) = 정확히 2,297`
- 2,297 = `large_attributes.json`의 leaf path 수와 일치
- 1,536 = **OpenAI `text-embedding-ada-002`** 차원과 일치
- 결론: 원본 pickle은 ada-002로 인코딩된 2,297 × 1,536 float64 ndarray

---

## 7. Pickle 재생성 원리

### Q. 1번(재생성)은 무슨 뜻인가?

"복구"가 아니라 **재료에서 새로 만드는** 것:
- 입력 (= 슬롯 경로 문자열): `data/large_attributes.json`에 그대로 보존
- 변환기 (= 모델): `text-embedding-ada-002` — 결정론적 (같은 input → 항상 같은 vector)
- 출력 형식 (= 코드가 기대): `{"attribute_paths": [...], "embeddings": ndarray}` 확인됨

비유: 콩가루 통이 깨졌지만 콩과 분쇄기가 그대로 → 다시 갈면 끝.

### Q. 어떤 원리로 복구한다는 것인가?

- SentenceTransformer/OpenAI ada-002 모델 weights는 **고정**
- 같은 weights + 같은 input → 부동소수점 수준에서 동일한 벡터
- 즉 복구가 아닌 **재계산** (재현 가능성을 활용)

**비용/시간**:
- 2,297 path × ~10 token = 약 23,000 tokens
- ada-002 가격: $0.0001 / 1K tokens → **약 $0.0023 (3원)**
- 소요: 1-3분

---

## 8. 시스템 동작 원리 심층 이해

### Q. pickle 파일로 이미 페르소나를 생성해 놓은 것인가?

**아니요. 정확히 거꾸로.**

| 항목 | 정체 |
|---|---|
| Pickle | 8천여 개 **속성 카테고리**의 의미 벡터 lookup table |
| 페르소나 | runtime에 OpenAI API로 **매번 새로 생성** |
| HuggingFace dataset (`THzva/deeppersona_dataset`) | 이미 생성해둔 페르소나 모음 |

**논문의 진짜 기여**:
1. 8,000+ attribute **taxonomy** (ChatGPT 대화에서 mining한 인간 속성 분류)
2. Depth-first 생성 **파이프라인**
3. Attribute selection **방법론** (가까운/먼 vector 섞어 다양성 + 깊이 동시 확보)
4. 검증된 정량 gain (+32% diversity, +44% uniqueness)

### Q. 페르소나 단어(상냥함 등) 8천 개에 대한 임베딩값을 미리 생성해놓은 것인가?

**핵심 교정**: 8,000+는 "성격 단어"가 아니라 **계층적 속성 슬롯**.

실제 데이터 구조:
```
Career and Work Identity.Background.technicalSkills
Personality.Temperament.Patience
Lifestyle.Hobbies.gardening
```

→ "온화함을 중시하는 사람"이라는 값(value)이 아니라, "그런 값을 담을 수 있는 슬롯(structure)".

**Leaf 경로 수**: 2,297개 (README의 "8,000+"는 inner node 포함 추정).

### Q. 슬롯 제목만 임베딩하면, 실제 성격값(상냥하다)을 어떤 슬롯에 매핑할지는 어떻게 판단하나?

**매핑 방향이 직관과 반대**입니다.

실제 흐름:
```
[Step 1] based_data.py: 시드 인물 정보 생성 (LLM)
   나이/직업/가치관/인생이야기/취미

[Step 2] 시드 정보를 텍스트 요약 → text-embedding-ada-002로 벡터화

[Step 3] 시드 벡터와 2,297개 슬롯 벡터의 cosine similarity 계산

[Step 4] 50:30:20 비율로 200개 슬롯 선택
   가까움 100개 (관련성) + 중간 60개 (다양성) + 먼 40개 (의외성)

[Step 5] 선택된 200개 슬롯을 LLM에 넘김
   "이 사람의 'Career.Background.tech'에 어떤 값이 어울릴까?"
   → LLM이 "Python, SQL, B2B 채널 전략" 같은 실제 값 생성
```

| 사용자 가정 | 실제 |
|---|---|
| 값 → 슬롯 분류기 | 시드 인물 → **관련 슬롯들 발견기** |
| 임베딩이 값을 결정 | 임베딩은 슬롯만 고름, **값은 LLM이 별도 생성** |

비유: 도서관에 책장 라벨 8천 개 → 손님 관심사로 어울리는 책장 라벨들 찾기 → 책장마다 손님 맞춤 책을 작가(LLM)가 새로 씀.

### Q. Pickle은 50:30:20 선택을 빠르게 하려고 만든 것인가?

**정확히 그것 하나의 목적입니다.**

| 비용 항목 | 캐시 없음 | 캐시 (pickle) |
|---|---|---|
| 페르소나 1개당 슬롯 임베딩 호출 | 2,297번 | 0번 (dict lookup) |
| 페르소나 1개당 시드 임베딩 호출 | 1번 | 1번 |
| 100,000개 생성 비용 | $23,000 | $10 |

비대칭의 원리:
- **슬롯 임베딩**: 2,297개 텍스트가 고정 → 한 번 만들어두면 영원히 재사용
- **시드 임베딩**: 페르소나마다 다른 사람 → 매번 새로 계산 (캐시 불가)

알고리즘 자체는 pickle 없이도 동일하게 작동. 단지 매번 OpenAI API에 호출만 더 들어갈 뿐.

---

## 9. 비교 가능성 vs 다양성 트레이드오프

### Q. 2,297개 슬롯 중 200개만 임의로 뽑으면 사람마다 슬롯 자체가 달라서 비교 가능성을 해치지 않나?

**날카로운 지적 — 이게 논문의 의도된 설계 선택**.

| | 전통 (Big Five, MBTI) | DeepPersona |
|---|---|---|
| 슬롯 구성 | 모두 동일한 N개 | 사람마다 다른 200개 부분집합 |
| 비교 용이성 | O | X (직접 비교 불가) |
| 깊이/다양성 | X | O |

**그러나 코드를 보면 하이브리드 구조**:

```
[Layer 1] 공통 base_info (모든 페르소나 동일)
   나이, 성별, 위치, 직업, 가치관, 인생태도, 인생이야기, 취미

[Layer 2] 12개 top-level 카테고리 (Career만 예외적으로 제외 가능)
   Career, Demographics, Lifestyle, Personality, Values, ...
   → 카테고리 수준 비교 가능: "A는 Career 슬롯 18개, B는 24개"

[Layer 3] Leaf 슬롯 2,297개 중 200개 (사람마다 다름)
   → 직접 비교 불가, 다양성 확보 layer
```

**가능한 비교 종류**:
| 비교 차원 | 가능? |
|---|---|
| 인구학적 분포 | O |
| 12개 카테고리 attribute count | O |
| 개별 slot 직접 비교 | X |
| Summary text 임베딩 유사도 | O |
| 통계적 학습 (LLM 훈련) | O |

**사용처별 적합도**:
| 사용처 | 적합도 |
|---|---|
| 사회 시뮬레이션 | ★★★★★ |
| 개인화 LLM 훈련 | ★★★★★ |
| 인간-AI 정렬 연구 | ★★★★ |
| 심리학 비교 연구 (Big Five 점수 분포) | ★★ |
| A/B 테스트용 user cohort | ★★ |

**통계적 시각**:
- 사람마다 슬롯이 달라도 모집단(2,297)과 선택 분포(5:3:2)는 일정
- 충분한 표본에서 메타 분포 기반 통계 가능
- Longitudinal survey에서 응답 항목 일부 다른 것과 유사

**결론**: 비교 가능성과 다양성은 동시에 가질 수 없는 trade-off. 논문은 다양성을 선택했고, 비교가 필요하면 별도 도구를 쓰는 것을 전제한 설계.

---

## 10. Nemotron-Personas-Korea와의 결합 전략

### Q. 이 논문과 [Nemotron-Personas-Korea](https://huggingface.co/datasets/nvidia/Nemotron-Personas-Korea) 데이터셋을 어떻게 활용하면 좋을까? 혼용해서 더 나은 사용방법을 만들어내고 싶은데

두 데이터셋의 성격을 비교해보면 놀라울 정도로 **상호보완적**입니다:

| | DeepPersona | Nemotron-Personas-Korea |
|---|---|---|
| 핵심 강점 | **깊이** (200 attr/페르소나, 1MB narrative) | **현실성** (KOSIS 인구통계 기반, 1M명) |
| 약점 | 인구통계 미연결, 영어 taxonomy | 페르소나당 7개 narrative + 6개 attribute로 얕음 |
| 언어 | 영어 (ChatGPT 대화에서 채굴) | 한국어 |
| Schema | 사람마다 다른 200 슬롯 (비교 어려움) | 26개 고정 필드 (비교 쉬움) |
| 라이선스 | MIT | CC BY 4.0 |

DeepPersona의 약점(인구통계 grounding 부족, 한국어 미지원)을 Nemotron이 정확히 메우고, Nemotron의 약점(개별 인물 얕음)을 DeepPersona가 메웁니다.

**전략 4가지** (난이도 순):

| 전략 | 핵심 아이디어 | 비용 | 가치 |
|---|---|---|---|
| **A. Seed 교체** | DeepPersona의 `based_data.py`를 Nemotron 1개 sampling으로 교체 → 한국 실제 인구통계 위에 DeepPersona 깊이 얹기 | $$ (OpenAI API/persona) | 한국어 깊은 페르소나 즉시 생성 가능 |
| **B. 한국형 Taxonomy 채굴** | Nemotron 1M 페르소나에서 한국 문화 attribute(군대, 수능, 시댁관계, 회식 등) 추출 → DeepPersona taxonomy 확장 | $$$ (mining pipeline) | 한국 문화 sensitive한 taxonomy 자산 구축 |
| **C. Hybrid Schema** | Nemotron 26개 필드 = 비교가능 backbone, DeepPersona 200 슬롯 = 다양성 layer를 한 페르소나에 동시 탑재 | $$ | study.md #9의 하이브리드를 실제 구현 |
| **D. 벤치마크 / Cross-walk** | 두 데이터셋을 downstream task(개인화 LLM 훈련, 사회 시뮬레이션)에 같이 넣어 어느 게 어느 작업에 좋은지 비교 | $ | 논문 contribution 가능 |

**가장 큰 trade-off**:
DeepPersona의 taxonomy는 **영어 ChatGPT 대화에서 채굴**되어 한국 고유 attribute(군대 경험, 입시, 시댁/처가, 회식 문화, 종교 분포 등)가 부재합니다. Strategy A만 단독으로 쓰면 "한국 인구통계 + 미국식 사고방식" 같은 어색한 페르소나가 나올 위험이 있습니다.

**추천**: **A + B 결합** (또는 단계적으로) — Nemotron 시드 위에 DeepPersona 파이프라인을 돌리되, taxonomy 자체에 한국 문화 슬롯을 보강. 가장 자연스러운 fusion이고, 결과물(한국 문화 grounded deep persona generator)은 둘 중 어디서도 단독으로 만들 수 없는 것입니다.

용도가 무엇인지(개인화 LLM 훈련용 데이터, 시뮬레이션, 연구 등)에 따라 전략 우선순위가 바뀜.

---

## 11. 참고 사례: 06_kintents 프로젝트의 혼용 전략

### Q. `/Users/eugene/Dropbox/K3I_PC/coding/06_kintents` 에서도 2개 방식을 혼용 중. 어떻게 혼용하는가?

다른 프로젝트(`06_kintents`)의 코드와 문서를 전수 조사한 결과 — 명확한 **2단계 layering 전략** 사용 중.

### 11-1. 2단계 파이프라인 구조

코드 위치: `apps/api/app/domain/persona/audience_persona.py`

```
[Stage 1] Bias-free Anchor 샘플링 (LLM 호출 X)
   _sample_anchor_from_table()
   - nvidia_korea_anchors.json에서 결정론적 sampling
   - 나이/성별/도시/직업/value_type 결정
   → PersonaAnchorBase 객체

           ↓ anchor를 context로 주입

[Stage 2] DeepPersona Progressive Enrichment (LLM 호출)
   DeepPersonaGenerator.generate()
   ├─ _gen_values_section()     ← core values
   ├─ _gen_attitude_section()   ← life philosophy
   ├─ _gen_life_section()       ← personal stories
   ├─ _gen_hobbies_section()    ← interests
   ├─ _gen_nvidia_korea_tech_profile()  ← domain extension
   ├─ _gen_other_attributes()   ← 5:3:2 taxonomy strata sampling
   └─ _gen_summary()            ← 통합 narrative
   → DeepPersonaFullProfile (target 200-250 attributes)
```

### 11-2. 핵심 의도 (claude.md:1870 verbatim)

> "DeepPersona 방법론에 따라 이 값들은 LLM이 아닌 **사전 정의 테이블에서 샘플링**하여 bias-free value assignment를 보장한다."

→ Stage 1을 LLM이 아닌 통계 분포에서 **결정론적으로** 뽑는 이유: LLM이 demographic hallucination(예: "한국 데이터 사이언티스트는 다 서울 거주" 같은 편향)을 일으키지 못하게 막기 위함. Nemotron의 통계 grounding 철학을 작은 distribution table로 모사.

### 11-3. 중요한 caveat — Nemotron 원본을 직접 쓰지 않음

`providers/taxonomy_data/nvidia_korea_anchors.json`은 NVIDIA의 1M 페르소나 데이터셋이 **아니라** 그 스피릿만 차용한 축소 분포표:
- 8개 직업 (software_engineer, data_scientist, game_developer 등)
- 4개 나이 그룹 (20대~50대)
- 6개 도시 (서울 45%, 경기 20%, 부산 10% 등)
- 성별 분포 (남 68%, 여 32%)

→ Nemotron의 26개 필드 / KOSIS 기반 정밀 분포를 다 가져온 게 아니라, 자신의 도메인(IT/GPU 관련 비디오 평가)에 필요한 축약된 anchor만 정의.

### 11-4. 현재 구현 상태

`개발과정스터디.md:197`에 명시: **Stage 2의 section generation은 아직 LLM 미연결, 하드코딩 템플릿 반환 중**.
- ✅ Stage 1 anchor sampling, taxonomy loader, schema, evaluation rubric (10-metric: PF/AC/DS/JU/ACT/ER/NR/DV/GP/EM) 완성
- ⬜ `_gen_values_section()` 등 LLM 호출 부분은 stub (Phase 4 TODO)
- 현재 attribute_count ~120 (목표 200-250 미달)

### 11-5. 최종 스키마 (`DeepPersonaFullProfile`)

```python
{
    "id": UUID,
    "source_label": "NVIDIA_KOREA_PERSONA",
    "anchor": PersonaAnchorBase,      # Stage 1
    "sections": dict,                  # Stage 2 — 7 sections
    "attribute_count": int,
    "nvidia_korea_tech_profile": {...},  # GPU 지식, AI 도구 사용, 브랜드 로열티
    "content_reaction_rubric": {...},
    "big_five": dict,
    "generation_method": "DEEPPERSONA_V1",
}
```

→ PostgreSQL `audience_personas.deep_persona_layers` JSONB 컬럼에 저장.

### 11-6. study.md §10의 전략 분류와 매핑

| §10 분류 | 06_kintents 채택 여부 |
|---|---|
| Strategy A (Seed 교체) | ✅ 핵심 채택 — Nemotron-style 분포로 시드 결정 |
| Strategy B (한국형 Taxonomy 채굴) | ❌ 안 함 — 자체 도메인 taxonomy 사용 |
| Strategy C (Hybrid Schema) | ⚠ 부분 — anchor=고정 backbone, sections=가변 layer |
| Strategy D (벤치마크) | ❌ 안 함 |

### 11-7. 가장 흥미로운 차이점

이 프로젝트는 Nemotron 원본 **데이터셋(1M)**을 활용하지 않고 **방법론적 통찰**(bias-free 통계 grounding) 만 가져와서 자기 도메인용 **축소 분포표**로 다시 만들었음:
- Nemotron의 **1M 페르소나 자체** = 미활용
- Nemotron의 **PGM + 공식 통계 grounding 사상** = 단순화해서 차용
- DeepPersona의 **progressive section + taxonomy strata 알고리즘** = 그대로 차용 (5:3:2 비율 포함)

### 11-8. 본 fork에서 시사점

한국 페르소나를 만들 때 두 방향이 있음:
1. **06_kintents 방식**: Nemotron 1M을 안 쓰고 작은 분포표 만들기 → 빠르고 가벼움, 통계 충실도 손실
2. **§10 Strategy A 방식**: Nemotron 1M에서 직접 1개를 뽑아 seed로 사용 → 더 충실, schema 매핑 작업 필요

"통계적 정밀도 vs 구현 단순성" trade-off.

---

## 12. Strategy A 상세 분석

### Q. Step 1, 2만 Nemotron 직접 sampling으로 대체하고, Step 3, 4, 5는 DeepPersona 절차를 그대로 따른다는 것인가?

**핵심 골자는 정확.** 두 개의 미세한 문제만 처리하면 됨.

### 12-1. 사용자 이해의 매핑

```
[Step 1] based_data.py로 시드 생성 (LLM 호출)
    → Nemotron-Korea에서 1개 record 샘플링 (LLM 호출 0회)

[Step 2] 시드를 텍스트 요약 → ada-002 임베딩
    → Nemotron record를 요약 text로 합쳐서 → 동일하게 ada-002 임베딩

[Step 3] cosine similarity vs 2,297 슬롯  →  변경 없음
[Step 4] 50:30:20 선택                  →  변경 없음
[Step 5] LLM이 200개 슬롯에 값 채움      →  변경 없음
```

이 흐름이면 DeepPersona 코드 수정 범위가 매우 작음 — `based_data.py`의 출력 형식만 Nemotron sampling에 맞춰 mapping해주면 끝.

### 12-2. 문제 1: 시드 텍스트 구성 (Step 1.5)

Nemotron 1개 record의 26개 필드 중 어떤 걸 시드 summary에 넣을지 설계 필요:

| Nemotron 필드 | Step 2 시드 포함? | DeepPersona 대응부 |
|---|---|---|
| `persona` (요약) | ✅ 핵심 | personal_story |
| `professional_persona`, `family_persona` 등 7개 narrative | ✅ 모두 | personal_story + values + attitudes 합본 |
| `cultural_background`, `skills_*`, `hobbies_*`, `career_goals_*` 6개 | ✅ 모두 | values + interests |
| `age`, `sex`, `occupation`, `province`, `education_level` 등 key 5-6개 | ✅ | based_data의 age/gender/career/location |
| `marital_status`, `military_status`, `family_type`, `housing_type`, `district` 등 | ⚠ 선택 | DeepPersona엔 대응부 없음 (오히려 정보 추가) |

→ 단순 concat은 임베딩이 노이즈에 묻힘. **선택과 가중치** 설계 필요.

### 12-3. 문제 2: 언어 mismatch가 Step 3 정확도를 떨어뜨림

- Nemotron 시드 텍스트 = **한국어** ("32세 남성, 게임 개발자, 서울 거주, 등산 좋아함...")
- DeepPersona 슬롯 텍스트 = **영어** ("Career and Work Identity.Background.technicalSkills")
- ada-002는 multilingual이지만 **cross-lingual cosine similarity는 same-lingual보다 정확도 ↓**
  - "등산을 좋아함"이 `Hobbies.Outdoor.Hiking`과 가까운지 발견 못 할 수 있음
  - 슬롯 선택이 무관한 쪽으로 쏠릴 위험

**해결 옵션**:
- **A**: Step 2에서 시드를 한국어→영어 1회 번역 후 임베딩 (1 LLM call 추가, 정확도↑)
- **B**: 슬롯 텍스트도 한국어 임베딩 새로 생성 (pickle 2개 운영)
- **C**: 시드 임베딩만 multilingual 모델로 교체 (e.g., `text-embedding-3-large`로 일관 통일)

### 12-4. 문제 3: 미반영되는 한국 고유 슬롯

DeepPersona 2,297 슬롯에 다음 한국 특수 attribute가 **부재**:
- 군대 경험 / 군 보직
- 수능 점수 / 입시 경로
- 시댁/처가 관계
- 회식 문화 적응도
- 거주지 자가/전세/월세
- 세대갈등 인식

→ Step 4에서 아무리 잘 골라도 **이 슬롯들이 200개 안에 들어올 수 없음**.

Nemotron이 `marital_status`, `military_status`, `family_type`, `housing_type`을 이미 갖고 있는데, DeepPersona 200 슬롯에서는 빠짐 → 두 데이터셋의 강점이 어긋남.

**Step 5 부분 보완**: LLM prompt에 "이 사람은 한국인이니 군 경험, 입시 같은 Korean-specific context를 narrative summary 단계에서 반영하라" 지시. 다만 슬롯 자체가 없으니 구조화된 attribute로 잡히진 않음.

### 12-5. 사용자 직관 평가

| | 정확도 |
|---|---|
| Step 1, 2를 Nemotron sampling으로 대체하는 발상 | ✅ 정확 — 가장 빠르고 효과적인 Strategy A 구현 |
| Step 3, 4, 5를 그대로 가져가는 발상 | ✅ 대부분 정확 — 알고리즘 자체는 그대로 동작 |
| 단, 결과 품질을 위해 추가 처리 필요 | ⚠ 시드 텍스트 구성 + 언어 mismatch 보정 + 한국 고유 슬롯 누락 인지 |

### 12-6. 최소 구현 변경 list

Strategy A를 실제로 코딩한다면:

1. `based_data.py` → `nemotron_anchor.py`로 대체 (Nemotron parquet/json 로드 + `random.choice`)
2. `_extract_profile_summary()` → Nemotron 필드를 매핑하는 새 버전 작성
3. (옵션) `_create_profile_embedding()` 직전에 시드를 영어로 1회 번역
4. (옵션) Step 5의 LLM prompt에 "한국 문화 맥락 반영" 지시 추가
5. (이상적) Step 4 결과에 Nemotron의 demographic 필드(군대/혼인/주거)를 **무조건 포함**하도록 hybrid 구조 추가

이게 §11의 06_kintents 프로젝트가 _이미_ 시작한 일 — 다만 그쪽은 Nemotron 원본 1M을 안 쓰고 **자체 축소 분포표**로 출발. 본 fork에서 더 충실하게 Nemotron을 직접 활용한 Strategy A를 진행할 수 있는 단계.

---

## 13. Pickle 재생성 후 attribute_count sweep과 README 주장 검증

### 13-1. 실행 결과

`scripts/regenerate_embeddings.py` 실행 → 27.05MB 정상 pickle 복구. 직후 smoke test:

| `attribute_count` | 시간 | profile 크기 | 실제 attrs | KB/attr |
|---|---|---|---|---|
| 100 (smoke test) | 31.7s | 9.0 KB | 53 | 0.17 |
| 200 | 38.0s | 13.3 KB | 94 | 0.14 |
| 300 | 55.7s | 20.1 KB | 145 | 0.14 |
| **350 (max)** | **74.2s** | **27.4 KB** | **200** | **0.14** |

(이전 broken pickle 상태: 모든 setting에서 1.9 KB / 0 attrs)

### 13-2. README 주장 vs 실제

- README 주장: "~1 MB per persona, narrative-complete", "two orders of magnitude deeper"
- 실제 max (count=350): **27.4 KB → 1024 KB의 2.7%, 약 37배 격차**
- 선형 스케일링 일관 (0.14 KB/attr): 1MB 도달하려면 ~7,300 attrs 필요, but taxonomy max는 2,297 leaf path

### 13-3. 격차의 진짜 원인 — generate_profile.py의 카테고리 drop 버그

`selected_paths.json` 조사 결과:
- 19개 top-level 카테고리, 총 350 leaf path 정상 선택됨
- 그러나 `generate_profile.py`는 **6개 카테고리만 명시적으로 처리**:
  - Demographic Information
  - Career and Work Identity
  - Core Values, Beliefs, and Philosophy (single specific variant)
  - Lifestyle and Daily Routine
  - Cultural and Social Context
  - Hobbies, Interests, and Lifestyle
- **나머지 13개가 silently drop**:
  ```
  Media Consumption and Engagement
  Education and Learning
  Psychological and Cognitive Aspects
  Physical and Health Characteristics
  Relationships and Social Networks
  Emotional and Relational Skills
  Core Values and Beliefs               ← 거의 중복 variant
  Core Values and Philosophy            ← 거의 중복 variant
  Core Values, Beliefs, Philosophy      ← 거의 중복 variant
  Lifestyle and Routine                 ← 거의 중복 variant
  Lifestyle and Habits                  ← 거의 중복 variant
  Cultural and Social Contexts          ← 거의 중복 variant
  Psychological and Cognitive           ← 거의 중복 variant
  ```
- 코드는 `selected_paths.get("Other Attributes")`로 이들을 잡으려 하지만, 실제 데이터는 "Other Attributes" 키 아래로 묶이지 않음 → 분기 매번 fail
- 19개 중 6개 (32%) 만 처리됨

### 13-4. 격차 분해

| 격차 원인 | 영향 |
|---|---|
| 13/19 카테고리 누락 (Other Attributes 분기 bug) | 가장 큼 (×3 손실) |
| 중복 카테고리 variant 미통합 (`merge_tree.py` 미적용) | 중간 |
| `_check_if_career_needed`의 가끔 false (Career 전체 skip) | 작음 |
| Attr당 narrative가 짧음 (~140 byte/attr) | 보통 |

### 13-5. 가능한 개선 → 1MB 목표 추정

- 19개 카테고리 모두 처리 → 27 KB × ~3 = 80~100 KB
- 중복 variant 통합 후 → 약간 추가 향상
- LLM verbose 모드 → 200~300 KB
- **그래도 1MB 미달** → README 광고가 실제 능력보다 과장

### 13-6. 시사점

1. Pickle 재생성으로 vector search 자체는 정상 동작 확인 ✅
2. README의 "1MB" 주장은 현재 코드 path로는 도달 불가
3. 다음 bottleneck은 **embedding이 아니라 generate_profile.py의 카테고리 매핑**
4. 진짜 1MB 달성하려면: (a) 카테고리 매핑 수정 + (b) attribute당 narrative 길이 증가 + (c) taxonomy 정규화 — 모두 필요

---

## 14. Nemotron 1M records vs 7M personas — 단위 혼동 정리

### Q. Nemotron은 700만 개의 페르소나를 포함한 100만 건의 레코드라는데 데이터셋의 숫자가 700만인가 100만인가

**결론**: 사람은 **100만 명**, 한 사람당 7개의 "관점별 페르소나 텍스트"가 있어서 텍스트 블록 단위로는 **700만 개**.

### 14-1. 1 record = 1 person

각 레코드는 한 명의 가상 인물. 26개 필드 중 **7개가 관점별 페르소나 narrative**:

```
record_001 (= 한 명의 사람, 예: 32세 게임개발자)
├─ professional_persona  : "수년간 모바일 게임 개발에 종사하며 Unity와 Unreal..."
├─ sports_persona        : "주말마다 한강에서 자전거를 타고, 풋살 동호회 활동..."
├─ arts_persona          : "K-인디 음악과 일본 애니메이션을 즐겨 감상..."
├─ travel_persona        : "도시 여행보다는 자연 명소 선호, 제주도 단골..."
├─ culinary_persona      : "매운 음식 마니아, 자취 요리를 즐김..."
├─ family_persona        : "외동아들, 미혼, 부모님과 주 1회 통화..."
└─ persona               : (위 6개를 합친) 간결한 종합 요약
+ 19개의 attribute/demographic 필드
```

### 14-2. 산수

- 1,000,000 records × 7 persona 필드 = **7,000,000 텍스트 블록**

### 14-3. 왜 한 인물에 7개나?

| 의도 | 효과 |
|---|---|
| 다각도 설명 | 단일 narrative보다 풍부한 컨디셔닝 |
| 용도별 분리 사용 | "여행 LLM 훈련엔 travel_persona만 추출" 가능 |
| 필드별 비교 | "직업 narrative 분포" 같은 메타 분석 가능 |
| 마케팅 임팩트 | "7M personas"라고 강조하면 숫자 커 보임 |

### 14-4. 단위별 정리

| 단위 | 값 | 의미 |
|---|---|---|
| 인물 (records) | 1,000,000 | 시뮬레이션 가능한 distinct 사람 수 |
| 페르소나 텍스트 | 7,000,000 | LLM 컨디셔닝 가능한 narrative 단위 |
| 토큰 | 1.7B (그중 1B = persona text) | 학습 데이터 부피 |
| 고유 이름 | 209,167 | 79% 레코드가 동명이인 (실제 한국 작명 패턴 반영) |

### 14-5. DeepPersona와 단위 비교

| | DeepPersona | Nemotron-Korea |
|---|---|---|
| 한 사람 = | 1 profile | 1 record |
| 한 사람의 narrative 블록 수 | 1 (Summary + structured attrs) | 7 (관점별 분리) |
| narrative당 글자수 | 길고 통합적 (수천 단어) | 짧고 관점별 (수백 단어 × 7) |
| 사람 수 (현재 코드 기준) | 무한 (매번 새로 생성) | 1M 고정 |

### 14-6. Strategy A에서의 활용

- Nemotron 1M 중 1명 sampling → 7개 persona 텍스트 + 19개 attribute = DeepPersona의 시드(Step 1)로 충분히 풍부
- 7개 텍스트 모두 시드 summary에 합치면 → ada-002 임베딩이 다각도로 잡힘 → Step 3 cosine search 품질↑
- 용도별 선택 가능: "직업 시뮬레이션엔 professional_persona만"

### 14-7. 마케팅 워딩 주의

"1M records containing 7M personas"는 두 숫자를 모두 활용한 표현. 실제 distinct 인물은 1M, "페르소나"라는 단어를 narrative 블록 단위로 카운트해 7M로 부풀린 것. 둘 다 사실이지만 단위가 다름.

---

## 15. 응용 비전: 고대 한국인 NPC 생성 (XR 게임/앱)

### Q. 2개 페르소나 방식을 mix하면서 궁극적으로 "백제, 신라 등 특정 시대 우리민족 모사(7세기 통일신라인, 4세기 백제인 등)"하는 다수 고대인 에이전트 생성. XR 기반 게임/앱에서 NPC로 그 시대 사람처럼 행동·대화. 어떻게 추가 구현할까?

이건 단순 데이터셋 혼용을 넘어 **"시대 변환(temporal transcoding)"** 이라는 새 문제 카테고리.

### 15-1. 핵심 도전 과제 5가지

| 도전 | 본질 | 난이도 |
|---|---|---|
| **1. 시대 적합성** | 현대 LLM은 21세기 사고에 saturated. 7C 신라인은 민주주의/개인주의/과학 개념 없음 | ★★★★★ |
| **2. 데이터 희소성** | Nemotron=2024 통계, DeepPersona=영어 ChatGPT mining → 둘 다 고대 학습 없음 | ★★★★★ |
| **3. Schema 재설계** | 신분(골품/육두품), 신앙(불교/도교/무속), 가문, 부족 정체성 등 현대 26필드와 무관 | ★★★★ |
| **4. 행동 fidelity** | 말투 + 결정 + 금기 + 세계관 + 신화적 시간감각 일관성 | ★★★★ |
| **5. XR 런타임 제약** | NPC 응답 < 2초, 다수 동시 대화, 음성 출력, 메모리 한정 | ★★★ |

### 15-2. 전략 옵션 6가지

#### Strategy α — Prompt Conditioning Only (가장 빠름)
- 기존 DeepPersona 파이프라인 그대로, prompt에만 "7세기 신라인" 컨디션 강제
- Step 5 LLM에 system prompt: "이 사람은 7C 통일신라인. 골품제 인식, 불교, 농경, 화랑 정신..."
- **Pros**: 코드 변경 거의 없음, 즉시 시도 가능
- **Cons**: 모던 슬롯("Tech.AI tool usage")이 그대로 남아 anachronism, 모델 bias 새어나옴
- **적합도**: prototype, 데모용

#### Strategy β — Era-Specific Taxonomy 구축
- DeepPersona의 `large_attributes.json` 자리에 **고대 한국 attribute 트리** 새로 구축
- 예시 구조:
  ```
  사회적 정체성.골품제.출신골품 (성골/진골/육두품/오두품/...)
  사회적 정체성.가문.부 (왕족/육부귀족/지방호족/평민/노비)
  신앙체계.불교종파 (화엄/유식/계율/...)
  신앙체계.토속신앙 (산신/조상신/단군계)
  생업.농경/유목/장인/상인/관직
  세계관.천하관 (당-신라-왜의 위계 인식)
  관습.혼인제 (근친혼/족외혼)
  지식.문자 (한문/이두/구어만)
  ...
  ```
- **Pros**: 진정한 시대 충실성, vector search가 시대 적합 슬롯만 선택
- **Cons**: 한국 고대사 전문가 협업 필요, 수십 시간 mining
- **적합도**: 본격 연구, 박물관 협업

#### Strategy γ — Historical Demographic Anchor
- Nemotron의 KOSIS 접근을 고대 한국에 적용
- 추정 분포로 anchor 분포표 작성 (`silla_7c_anchors.json` 같은 형태)
- 학술적 인구 추정 (인구 50-100만명, 신분 분포 1:9:90 추정 등)
- **Pros**: 통계적 grounding, scale 가능
- **Cons**: KOSIS만큼 정밀한 통계 없음 — 학계 추정치 의존

#### Strategy δ — RAG로 사료 기반 증강
- 사료(삼국사기/삼국유사/일본서기/화랑세기) + 학술논문을 vector DB화
- 각 attribute 생성 시 시대 관련 passage 검색해 LLM에 주입
- **Pros**: 사실성↑, 검증 가능 ("이 NPC의 이 발화는 어느 사료에 근거?")
- **Cons**: 사료가 귀족 중심 → 평민 NPC는 RAG 빈약, 한문→한국어 처리 필요

#### Strategy ε — 도메인 특화 LLM 파인튜닝
- 사극/고전소설/번역사료/학술논문으로 작은 모델(7B급) 파인튜닝
- 페르소나 생성과 런타임 대화 모두 이 모델로
- **Pros**: 시대 mindset 내재화, on-device 가능 → XR latency↓
- **Cons**: 데이터 큐레이션이 가장 큰 작업, base 모델 bias 잔존

#### Strategy ζ — Multi-stage Hybrid (장기 비전)
```
Stage 1: γ로 인물 anchor 샘플링 (신분/지역/시대 정합)
Stage 2: β의 고대 taxonomy + Step 3-5는 DeepPersona pipeline
Stage 3: δ로 각 attribute에 사료 인용 주입
Stage 4: ε의 fine-tuned 모델로 런타임 대화
```
- **Pros**: 모든 측면 커버
- **Cons**: 1-2년 프로젝트 규모, 초기 투자 큼

### 15-3. 전략 매트릭스

| 우선순위 | 추천 전략 | 이유 |
|---|---|---|
| 빨리 데모/PoC 보고 싶다 | α + 약간의 β | 1주일 안에 prototype 가능 |
| 연구/논문/투자 유치 | β + δ | 차별성 있는 결과물, 사료 인용 가능 |
| 실제 출시 가능한 XR 앱 | ζ 축소판 (α+β+ε 일부) | 품질-비용-속도 균형 |
| 장기 핵심 자산 구축 | β + ε | 한국 고대 LLM이라는 platform 자산 |

### 15-4. NPC 행동 (런타임 — 별개 문제)

페르소나 **생성**과 **운영 시 대화**는 분리해서 봐야 함:

| 컴포넌트 | 관심사 | 옵션 |
|---|---|---|
| **말투** | 사극체 / 현대어 단순화 / 한자어 비율 | 시스템 프롬프트로 통제 가능 |
| **지식 경계** | "스마트폰" 같은 단어를 모름. 천문은 알지만 지동설은 모름 | 페르소나에 `knowledge_horizon` 필드 추가, LLM에 "이 사람이 모르는 것" 명시 |
| **결정 동기** | 충성/효/신분/불심/실리 중 어떤 게 dominant? | Big Five 대신 **시대 가치 5축** 설계 |
| **세계관** | 천하관, 시간감(불교 윤회/유교 천명), 공간감(당-신라-왜) | 페르소나에 `worldview_axioms` 필드 |
| **금기/터부** | 신분 무시한 발화 거부, 왕족 모욕 격노, 특정 음식/색 회피 | constraint list로 LLM 응답 필터 |
| **언어 출력** | TTS는 사극톤 한국어 정도가 현실적 | 별도 음성 파이프라인 |

→ 페르소나 JSON에 **behavioral spec**을 함께 저장해 runtime에 system prompt로 주입.

### 15-5. XR/게임 통합 고려사항

- **Latency**: 대화 응답 < 2초 필요 → 7B-13B 모델 로컬 추론, 또는 GPT-4o-mini 류 API + 짧은 응답
- **다수 NPC**: 페르소나 JSON 캐싱, 대화 시작 시 lazy load
- **세션 memory**: 짧은 conversation history만 유지, 장기는 episodic memory로 요약
- **음성**: 사극톤 TTS는 ElevenLabs voice cloning 가능 (한국 성우 데이터로)
- **시각**: 별도 — Stable Diffusion + 시대고증 ControlNet, MotionGPT 등

### 15-6. 권장: 4-Phase 점진 접근

```
[Phase 1, 1-2주] Strategy α + Nemotron 시드 변환 실험
  - 기존 DeepPersona를 그대로 돌리되, Nemotron 시드(현대 한국인)를
    프롬프트로 "7C 신라인으로 컨버전"
  - 결과 NPC와 대화해보고 어디서 깨지는지 정성 평가
  - 산출: PoC NPC 5-10명, "anachronism heatmap"

[Phase 2, 2-4주] Strategy β의 첫 버전 — 고대 taxonomy 1.0
  - 한국사 전공자/사학과 학생 1명과 협업
  - 50-100개 핵심 attribute부터 시작 (골품, 신분, 신앙, 생업, ...)
  - DeepPersona pipeline은 그대로, taxonomy만 교체
  - 산출: silla_7c_attributes.json, 다시 생성한 NPC 10명

[Phase 3, 1-2개월] γ + δ 결합
  - 신분/지역 추정 분포로 anchor table 작성
  - 삼국사기/삼국유사 chunking + embedding → RAG 시스템
  - attribute 생성 단계마다 관련 사료 인용 주입
  - 산출: 50-200명 cohort, 사료 인용 추적 가능한 NPC

[Phase 4, 3-6개월] ε의 일부 — runtime 모델 fine-tune
  - Phase 1-3에서 생성한 페르소나 + 대화 로그 + 사료를 학습 데이터화
  - 7B 모델 (Llama/Qwen) 파인튜닝
  - On-device 추론 가능 → XR 런타임 적합
  - 산출: 'silla_npc_chat-7b' 모델 + 100-500 NPC 카탈로그
```

### 15-7. 가장 작은 첫 걸음 (이번 주 가능)

**한 가지를 시작한다면**: Phase 1의 첫 실험.

```python
# 1. 현 DeepPersona 파이프라인에 era prompt만 주입
#    generate_profile.py의 LLM 호출에 시스템 메시지 추가:
SYSTEM = """이 페르소나는 7세기 통일신라 사람입니다.
- 골품제(성골/진골/육두품/오두품/사두품) 인식
- 불교, 농경사회, 화랑정신, 당과의 외교 의식
- 스마트폰/자동차/민주주의/과학 같은 현대 개념은 모름"""

# 2. attribute_count=200 으로 3명 생성
# 3. 각 페르소나의 attribute를 읽고:
#    - 시대 맞는 것 / 맞지 않는 것 분류
#    - 어떤 슬롯이 anachronism의 원흉인지 식별
#    → β 단계에서 어떤 슬롯을 만들고/없앨지 가이드
```

이 실험 결과만 봐도 본 프로젝트가 어떤 부분에서 가장 무너지는지 (taxonomy vs LLM bias vs schema), 다음 투자 우선순위가 명확해짐.

### 15-8. 요약

| 시점 | 추천 |
|---|---|
| 이번 주 | **α** 실험으로 anachronism map 파악 |
| 1-3개월 | **β + γ + δ** 결합으로 고대 한국 페르소나 생성기 구축 |
| 반년+ | **ε** 파인튜닝으로 XR 런타임 자산화 |

---

## 진행된 커밋 요약

| Commit | 내용 |
|---|---|
| `593f239` | MIT LICENSE + README fork attribution |
| `0331651` | `.env` 기반 secret loading (5개 파일) |
| `ab13f8a` | 하드코딩 `/home/zhou` 경로 제거 (5개 파일) |
| `f864d2f` | import-time 부수효과 버그 fix + smoke test script |
| `916633a` | 손상 pickle 재생성 (27MB, 2,297 × 1,536) + study.md 추가 |

## 미해결 / 다음 단계

**Runtime 복구**
- [x] `data/attribute_embeddings.pkl` 재생성 — 27.05MB, 정상 로드 확인 (916633a)
- [x] 재생성 후 smoke test 재실행 — 1.9KB → 9.0KB (count=100), 27.4KB (count=350)
- [ ] (선택) upstream `thzva/Deeppersona`에 pickle 손상 이슈 보고

**§13에서 도출된 generate_profile.py 버그**
- [ ] 13/19 카테고리 drop 문제 수정 — generate_profile.py가 하드코딩된 6개 카테고리 대신 selected_paths의 모든 top-level 키를 동적으로 처리하도록 변경
- [ ] (선택) `merge_tree.py` 실행해 거의 중복인 카테고리 variant들 통합
- [ ] 수정 후 attribute_count sweep 재실행해 80~100KB 도달 확인

**전략 실행** (§10-12에서 도출)
- [ ] Strategy A 구현 — `based_data.py` → `nemotron_anchor.py` 대체로 한국어 깊은 페르소나 생성
- [ ] Strategy A의 미세 문제 해결 (시드 텍스트 구성 + 언어 mismatch 보정 + 한국 고유 슬롯 보강)
- [ ] (장기) Strategy B — Nemotron 1M에서 한국 문화 attribute 채굴해 taxonomy 확장

**고대 한국 NPC 프로젝트** (§15에서 도출)
- [ ] Phase 1 — Strategy α PoC: era system prompt만 주입해 5-10명 신라/백제 NPC 생성, anachronism heatmap 작성
- [ ] Phase 2 — 고대 한국 taxonomy v0.1 (50-100 attribute) 설계
- [ ] Phase 2 보조 — 사학과 전공자 협업 채널 확보
- [ ] (중기) Phase 3 — 사료 RAG 인덱싱 + γ anchor table
- [ ] (장기) Phase 4 — 7B 모델 fine-tune for XR runtime

**Code hygiene** (선택)
- [ ] `extract_personalized_attributes.py:20` 등에 남아있을 수 있는 dataset 시점 path 잔재 확인
- [ ] sweep script (`scripts/test_attribute_count_sweep.py`) 커밋 여부 결정
