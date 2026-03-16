# WeatherCheck

여러 무료 날씨 API를 하나의 주소 기준으로 모아서 비교하는 표준 라이브러리 기반 웹 MVP입니다.

## 포함된 소스

- Open-Meteo
- MET Norway Locationforecast
- wttr.in
- 주소 변환: OpenStreetMap Nominatim

## 실행

```powershell
$env:WEATHERCHECK_CONTACT="your-email@example.com"
python .\app.py
```

브라우저에서 `http://127.0.0.1:8000` 을 열면 됩니다.

## 왜 연락처 환경변수가 필요한가

Nominatim과 MET Norway는 식별 가능한 `User-Agent`를 권장하거나 요구합니다. 그래서 `WEATHERCHECK_CONTACT`를 설정해서 요청 헤더에 포함합니다.

## 현재 MVP가 하는 일

- 주소 또는 `lat,lon` 좌표 입력
- 좌표 변환
- 각 소스별 현재 기온, 체감 기온, 상태, 6시간 강수 확률, 24시간 최저/최고 비교
- 3시간 간격 24시간 타임라인 비교
- 소스 간 현재 기온 편차와 강수 확률 편차 요약
- 소스별 실패를 개별적으로 표시

## 다음 단계 제안

- 소스 추가: WeatherAPI free tier, Tomorrow.io free tier, AccuWeather free tier
- 기간 비교: 시간대별 예보 테이블, 일별 예보 그래프
- 저장 기능: 관심 주소 presets
- 신뢰도 계산: 소스 간 편차 하이라이트

## 테스트

```powershell
python -m unittest discover -s .\tests -v
```
