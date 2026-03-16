# WeatherCheck

고정된 하나의 주소에 대해 여러 무료 날씨 API를 모아서 비교하는 웹 앱입니다.

## Fixed Location

- 표시 주소: `경기 연천군 장남면 장백로278번길 4`
- 실제 조회는 환경변수 좌표를 사용합니다.

## Run Locally

```powershell
$env:WEATHERCHECK_CONTACT="your-email@example.com"
$env:WEATHERCHECK_LATITUDE="37.0000"
$env:WEATHERCHECK_LONGITUDE="127.0000"
python .\app.py
```

브라우저에서 `http://127.0.0.1:8000` 을 열면 됩니다.

## Vercel

Vercel 환경변수에 아래 값을 넣어야 합니다.

- `WEATHERCHECK_CONTACT`
- `WEATHERCHECK_LATITUDE`
- `WEATHERCHECK_LONGITUDE`

## Current MVP

- 고정 주소만 표시
- 고정 좌표 기준 조회
- Open-Meteo, MET Norway, wttr.in 비교
- 현재 기온, 체감 기온, 상태, 6시간 강수 확률, 24시간 최저/최고 비교
- 3시간 간격 24시간 타임라인 비교
- 소스 간 편차 요약

## Test

```powershell
python -m unittest discover -s .\tests -v
```
