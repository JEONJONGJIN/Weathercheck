# WeatherCheck

고정된 하나의 주소에 대해 여러 무료 날씨 API를 모아서 비교하는 웹 앱입니다.

## Fixed Location

- 표시 주소: `경기 연천군 장남면 장백로278번길 4`
- 기본 조회 좌표: `37.9851297299633,126.886246142811`
- 기본 연락처: `jin0424@hanmail.net`
- 필요하면 환경변수로 덮어쓸 수 있습니다.

## Run Locally

```powershell
$env:WEATHERCHECK_CONTACT="your-email@example.com"
$env:WEATHERCHECK_LATITUDE="37.0000"
$env:WEATHERCHECK_LONGITUDE="127.0000"
python .\app.py
```

브라우저에서 `http://127.0.0.1:8000` 을 열면 됩니다.

## Vercel

Vercel 환경변수는 선택 사항입니다. 기본값이 코드에 들어 있습니다.

- `WEATHERCHECK_CONTACT`
- `WEATHERCHECK_LATITUDE`
- `WEATHERCHECK_LONGITUDE`
- `DATA_GO_KR_SERVICE_KEY`

## Current MVP

- 고정 주소만 표시
- 고정 좌표 기준 조회
- Open-Meteo, MET Norway, wttr.in 비교
- `DATA_GO_KR_SERVICE_KEY`가 있으면 기상청 동네예보 통보문 source 추가
- 현재 기온, 체감 기온, 상태, 6시간 강수 확률, 24시간 최저/최고 비교
- 3시간 간격 24시간 타임라인 비교
- 소스 간 편차 요약

## Test

```powershell
python -m unittest discover -s .\tests -v
```
