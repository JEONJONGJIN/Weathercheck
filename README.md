# 한솔스테이 날씨 조회

고정 주소 1곳을 기준으로 여러 날씨 소스의 예보를 한 화면에서 비교하는 웹 앱입니다.

## 고정 위치

- 주소: `경기 연천군 장남면 장백로278번길 4`
- 위도/경도: `37.9851297299633, 126.886246142811`
- 기본 연락처: `jin0424@hanmail.net`

기본값은 코드에 들어 있으므로, 별도 설정이 없어도 같은 위치를 조회할 수 있습니다.

## 현재 구성

- 메인 비교 표
  - 현재 기온
  - 체감 기온
  - 상태
  - 풍속
  - 강수량
  - 6시간 강수 확률
  - 24시간 최저/최고
  - 기준 시각
- 24시간 타임라인
  - 현재 시각 이후 기준
  - 3시간 간격 비교
- 기상청 중기예보
  - 3일~10일 전망 카드

## 현재 지원 소스

- `Open-Meteo`
  - 기본 비교 소스
- `OpenWeather`
  - `OPENWEATHER_API_KEY`가 있을 때 활성화
- `AccuWeather`
  - `ACCUWEATHER_API_KEY`가 있을 때 활성화
- `기상청 단기예보(data.go.kr)`
  - `DATA_GO_KR_SERVICE_KEY`가 있을 때 활성화
- `기상청 단기예보(API 허브)`
  - `KMA_APIHUB_AUTH_KEY`가 있을 때 활성화
- `기상청 중기예보`
  - `DATA_GO_KR_SERVICE_KEY`가 있을 때 하단 섹션에 표시

## 환경변수

선택 사항입니다. 기본값이 들어 있는 항목도 있습니다.

- `WEATHERCHECK_CONTACT`
- `WEATHERCHECK_LATITUDE`
- `WEATHERCHECK_LONGITUDE`
- `OPENWEATHER_API_KEY`
- `ACCUWEATHER_API_KEY`
- `DATA_GO_KR_SERVICE_KEY`
- `KMA_APIHUB_AUTH_KEY`
- `KMA_MID_LAND_REG_ID`
- `KMA_MID_TA_REG_ID`

## 로컬 실행

```powershell
python .\app.py
```

브라우저에서 `http://127.0.0.1:8000`을 열면 됩니다.

환경변수를 직접 넣고 실행하려면 예시는 아래와 같습니다.

```powershell
$env:WEATHERCHECK_CONTACT="your-email@example.com"
$env:OPENWEATHER_API_KEY="your-openweather-key"
$env:ACCUWEATHER_API_KEY="your-accuweather-key"
$env:DATA_GO_KR_SERVICE_KEY="your-data-go-kr-key"
$env:KMA_APIHUB_AUTH_KEY="your-kma-apihub-key"
python .\app.py
```

## Vercel 배포 메모

- 정적 파일은 `static/`
- API 엔드포인트는 `/api/forecast`
- Vercel 환경변수에 필요한 키를 넣고 redeploy 하면 됩니다.

주요 확인 항목:

- `OPENWEATHER_API_KEY`가 있으면 `OpenWeather` provider 표시
- `ACCUWEATHER_API_KEY`가 있으면 `AccuWeather` provider 표시
- `DATA_GO_KR_SERVICE_KEY`가 있으면 `기상청 단기예보(data.go.kr)`와 `기상청 중기예보` 표시
- `KMA_APIHUB_AUTH_KEY`가 있으면 `기상청 단기예보(API 허브)` 표시

## 알려진 사항

- OpenWeather 신규 키는 발급 직후 바로 동작하지 않고 몇 시간 뒤 활성화될 수 있습니다.
- AccuWeather 사용 시 공식 브랜드 표기 요구사항을 확인해야 합니다.
- 기상청 API 허브는 응답이 느릴 수 있어 일부 항목이 비어 보일 수 있습니다.
- 현재 앱은 주소 검색 없이 고정 위치만 조회합니다.

## 테스트

```powershell
python -m unittest discover -s .\tests -v
python -m py_compile .\weather_core.py .\app.py .\api\forecast.py
```
