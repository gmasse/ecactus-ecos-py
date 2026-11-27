# TODO List

## 🔥 High Priority
- [x] Standardize error returns using customized exceptions
- [x] API functions should return classes instead of JSON-like objects OR use pydantic for data validation
- [ ] Accept country in place of datacenter for client initialization
      (based on JSON from https://api-ecos-hu.weiheng-tech.com/api/client/guide/datacenter)

## 🚀 Medium Priority
- [ ] Increase unit test coverage
- [ ] Find and implement other devices type than inverter (ie battery, charger, ...)
- [ ] Implement other known API endpoints ([list](#uncovered-endpoints))
- [x] Implement uncovered errors ([list](#uncovered-errors))
- [ ] Create Enums for attributes `type`, `relation_type`, `state`, `master` in class `Home`, `Device`, and `charge_use_mode`, `strategy_mode`, `safety_standard` in class `Device`, `DeviceDetail`, `DeviceSettings`, `DeviceMode`

## 📌 Low Priority
- [ ] Identify and document any new API endpoints

---
_Last updated: 2026-11-27_



## Addendum
### Uncovered endpoints

Paths used by the ECOS web client (bundle of https://ecos.whes.com, 116 paths,
November 2026) that the library does not cover yet. "Verified" means the call
was tried against an Agave TH (three-phase, EU datacenter) on 2026-11-23.
Methods marked *(web)* are read from the web client, not tried. Writes were
never called.

#### Read-only, verified

- `POST /api/client/home/events/backup/list` — backup (EPS) events, paginated.
  Body: `{"deviceId", "startTime", "endTime" (epoch s), "pageSize", "pageNum"}`.
  Returns `{"totalPages", "totalCount", "data": []}`; no event was available to
  model the items.
- `GET /api/client/customize/info_last?deviceId=` — `{"chargingList": [], "dischargingList": []}`.
- `GET /api/client/v2/home/family/info?homeId=` — home details: time zone,
  currency, price type, device/member count, create/update time, PV capacity.
  Also returns coordinates and the members' contact data (personal data).
- `GET /api/client/v2/home/family/price_info?homeId=` — price type plus the
  fixed price (same data as `get_fixed_price`).
- `GET /api/client/ele/price/feed-in/get?homeId=` — `[]` without a feed-in tariff schedule.
- `GET /api/client/ele/price/retailer/get?homeId=` — `null` without a retailer.
- `GET /api/client/ele/price/use/get?homeId=` — `{"homeId", "monthUsePriceList": null}`.
- `GET /api/client/ele/price/wholesale/get?homeId=` — `null` without wholesale pricing.
- `GET /api/client/global/resource/category/tree` — catalogue of device series
  and types (e.g. series 101 "Single-phase", 102 "Three-phase" with type 20
  "Agave TH"); maps `resourceSeriesId`/`resourceTypeId` of `Device`.
- `GET /api/client/problem_feedback/country/list` — country list of the feedback form.

#### Read-only, need other parameters or permissions

Tried with `homeId`, `deviceId` and a millisecond `timestamp`, as GET and POST:

- `/api/client/v2/home/device/insight` — POST: `20000 cannot be null` (needs
  more fields, probably like the device insight: `periodType`, `timestamp`).
- `/api/client/customize/infoV2` — POST: `500 ... "mode" is null`.
- `/api/client/customize/dayAheadPrice` — POST: `20000 cannot be null`.
- `/api/client/customize/strategy/measurements` — POST: `20000 cannot be blank`.
- `/api/client/customize/strategy/compare`, `.../compare/prices`,
  `.../strategy/preview` — 403 (AI strategy, likely only when enabled).
- `/api/client/ele/price/retailer/price` — 403.
- `/api/client/message/page` — 403 (`count_unread` works as POST).
- `/api/client/problem_feedback/page`, `/detail` — 403 / not tried.
- `/api/client/v2/device/single/device/detail`, `.../single/device/power_limit`
  — single-phase counterparts of `get_device_detail` and `get_power_limit`. On
  the three-phase Agave TH they answer with the same keys as the `three/...`
  paths (2026-11-23, #91); not tried on a single-phase device.

#### Actions and settings (writes, not tried)

- `POST /api/client/v2/home/device/incrRefresh` `{"homeId"}` — returns
  `success` without data; effect unknown (maybe asks the devices for fresh data).
- Device settings: `/api/client/customize/...` updates *(web: POST)*,
  `/api/client/v2/home/device/remark`, `/removeAccount`, `/unbind`,
  `/transfer/family`, `/share/qrCode/client`, `/api/client/v2/home/install/upd`.
- Prices: `/api/client/ele/price/{fixed,feed-in,retailer,use,wholesale}/update`,
  `/feed-in/delete`, `/retailer/delete`, `/retailer/tibber/homes`,
  `/retailer/flatpeak/{connect-token,location-details,location-id}`.
- Homes and members: `/api/client/v2/home/family/{add,update,delete}`,
  `/api/client/v2/home/member/{invite,delete,exit}`, `/api/client/home/city/lookup`.
- Account: `/api/client/guide/loginPhone`, `/api/client/kraken/oauth/{login,login_phone}`,
  `/api/client/settings/user/{update,password,bindEmail,bindPhone,sendEmailBind,sendPhoneBind,delAccount,delAccountEmail,delAccountPhone}`.
- Messages and feedback: `/api/client/message/batch_mark_read`,
  `/api/client/problem_feedback/create`.
- AI assistant: `/api/client/v2/ai/chat/{completions,conversations}`.

#### Other device types (no device available)

- Charge station: `/api/client/v2/device/chargeStation/...` — `info`,
  `maxPower`, `startCharge`, `stopCharge`, `chargeMode/change`, `plug/switch`,
  `rcd/advancedSettings`, `capacity/history`, `chargeRecord/list`,
  `charge/card/{add,delete,query}`, `charge/task` (+ `/list`, `/update`, `/delete`).
- Smart plug: `/api/client/v2/device/singlePlugSocket/...` — `query`, `ele`,
  `switch`, `overcharge`, `clear/power`, `logs/switch`,
  `time/{countdown,random}`, `time/timing/{add,query,update,delete}`.

### Unknown device or home

Codes the live API answers for an identifier that does not belong to the
account (Agave TH, EU, 2026-11-23, #91). Most endpoints answer `20424` for a
device and `20450` for a home; these answer differently:

- `get_device_detail` — `20450` "The device does not exist.", the code of an
  unknown home; raised as `UnauthorizedDeviceError`.
- `get_power_limit`, `get_fault_events` — `20412` "illegal data operation";
  raised as `UnauthorizedDeviceError`.
- `get_cost_info` — success, every value `null`: an unknown home cannot be told
  apart from a home without cost data.
- `get_fixed_price` — success, `data: null`, the same answer as a home without
  a fixed price.
- `get_cost_info` with an identifier above the 64-bit range (e.g.
  `9876543210987654321`, the home id of the mock server) — HTTP 500
  `For input string: "9876543210987654321"`.

### Uncovered errors

Both cases below are already raised as `HttpError` with the HTTP status: since
#79, `_parse_response` maps any status >= 400 whose JSON body has no `code` to
`HttpError`. They remain listed as examples of the raw responses.

#### 405 Method Not Allowed
```
2025-02-15 10:34:23,213 - DEBUG - https://api-ecos-eu.weiheng-tech.com:443 "POST /api/client/v2/home/device/runData HTTP/1.1" 405 None
2025-02-15 10:34:23,213 - DEBUG - {"timestamp":1739633663171,"status":405,"error":"Method Not Allowed","message":"","path":"/v2/home/device/runData"}
```

#### 415 Unsupported Media Type
```
> POST /api/client/home/now/device/runData HTTP/1.1
> Host: api-ecos-eu.weiheng-tech.com
> Authorization: ***
> Content-Type: application/x-www-form-urlencoded
> 
* upload completely sent off: 33 bytes
< Content-Type: application/json
< 
* Connection #0 to host api-ecos-eu.weiheng-tech.com left intact
{"timestamp":1739636954905,"status":415,"error":"Unsupported Media Type","message":"","path":"/home/now/device/runData"}%
```
