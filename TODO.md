# TODO List

## 🔥 High Priority  
- [ ] API functions should return classes instead of JSON-like objects OR use pydantic for data validation

## 🚀 Medium Priority  
- [ ] Implement other known API endpoints ([list](#uncovered-endpoints))

## 📌 Low Priority  
- [ ] Identify and document any new API endpoints

---
_Last updated: 2025-02-02_



## Addendum
### Uncovered endpoints
#### /api/client/v2/home/device/energy

Request: `https://api-ecos-eu.weiheng-tech.com/api/client/v2/home/device/energy?homeId=1234567890987654321`

Output:
``` json
{
  "code": 0,
  "message": "success",
  "success": true
  "data": {
    "today": 1,
    "lastWeekTotalSolar": 125.7,
    "lastWeekTotalGrid": 145.1,
    "lastWeekTotalCarbonEmissions": 125.326,
    "lastWeekTotalSaveStandardCoal": 50.78,
    "weekEnergy": {
      "1": {
        "solarEnergy": 12.9,
        "gridEnergy": 3.8,
        "toGrid": 6.9,
        "homeEnergy": 9.8,
        "selfPowered": 61
      },
      "2": {
        "solarEnergy": 17.7,
        "gridEnergy": 29.6,
        "toGrid": 6.5,
        "homeEnergy": 40.8,
        "selfPowered": 27
      },
      "3": {
        "solarEnergy": 21.3,
        "gridEnergy": 18.9,
        "toGrid": 9,
        "homeEnergy": 31.2,
        "selfPowered": 39
      },
      "4": {
        "solarEnergy": 15.3,
        "gridEnergy": 19.8,
        "toGrid": 4.3,
        "homeEnergy": 30.8,
        "selfPowered": 36
      },
      "5": {
        "solarEnergy": 20.8,
        "gridEnergy": 17.4,
        "toGrid": 10.1,
        "homeEnergy": 28.1,
        "selfPowered": 38
      },
      "6": {
        "solarEnergy": 20.5,
        "gridEnergy": 22.3,
        "toGrid": 3.5,
        "homeEnergy": 39.3,
        "selfPowered": 43
      },
      "7": {
        "solarEnergy": 17.2,
        "gridEnergy": 33.3,
        "toGrid": 5.7,
        "homeEnergy": 44.8,
        "selfPowered": 26
      }
    },
    "carbonEmissionsWeekEnergy": {
      "1": {
        "carbonEmissions": 12.861
      },
      "2": {
        "carbonEmissions": 17.647
      },
      "3": {
        "carbonEmissions": 21.238
      },
      "4": {
        "carbonEmissions": 15.255
      },
      "5": {
        "carbonEmissions": 20.738
      },
      "6": {
        "carbonEmissions": 20.438
      },
      "7": {
        "carbonEmissions": 17.149
      }
    },
    "saveStandardCoalWeekEnergy": {
      "1": {
        "saveStandardCoal": 5.212
      },
      "2": {
        "saveStandardCoal": 7.15
      },
      "3": {
        "saveStandardCoal": 8.605
      },
      "4": {
        "saveStandardCoal": 6.181
      },
      "5": {
        "saveStandardCoal": 8.402
      },
      "6": {
        "saveStandardCoal": 8.282
      },
      "7": {
        "saveStandardCoal": 6.948
      }
    }
  }
}
```

#### /api/client/v2/home/device/incrRefresh

Request: `https://api-ecos-eu.weiheng-tech.com/api/client/v2/home/device/incrRefresh`
``` json
{
  "homeId": "1234567890987654321"            
}
```

Output:
``` json
{
  "code": 0,
  "message": "success",
  "success": true
}
```