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

## 진행된 커밋 요약

| Commit | 내용 |
|---|---|
| `593f239` | MIT LICENSE + README fork attribution |
| `0331651` | `.env` 기반 secret loading (5개 파일) |
| `ab13f8a` | 하드코딩 `/home/zhou` 경로 제거 (5개 파일) |
| `f864d2f` | import-time 부수효과 버그 fix + smoke test script |

## 미해결 / 다음 단계

**Runtime 복구**
- [ ] `data/attribute_embeddings.pkl` 재생성 (text-embedding-ada-002, 약 $0.003)
- [ ] 재생성 후 smoke test 다시 돌려 1MB 정상 profile 확인
- [ ] (선택) upstream `thzva/Deeppersona`에 pickle 손상 이슈 보고

**전략 실행** (§10-12에서 도출)
- [ ] Strategy A 구현 — `based_data.py` → `nemotron_anchor.py` 대체로 한국어 깊은 페르소나 생성
- [ ] Strategy A의 미세 문제 해결 (시드 텍스트 구성 + 언어 mismatch 보정 + 한국 고유 슬롯 보강)
- [ ] (장기) Strategy B — Nemotron 1M에서 한국 문화 attribute 채굴해 taxonomy 확장

**Code hygiene** (선택)
- [ ] Taxonomy 정리 — `Core Values and Beliefs` / `Core Values and Philosophy` / `Core Values, Beliefs, and Philosophy` 같은 거의 중복 카테고리 통합 (이미 `merge_tree.py` 존재)
- [ ] `extract_personalized_attributes.py:20` 등에 남아있을 수 있는 dataset 시점 path 잔재 확인
