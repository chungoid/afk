# Requirements-to-Files Mapping

| Requirement ID/Description          | Implementing File(s)                                                                                  |
| ----------------------------------- | ------------------------------------------------------------------------------------------------------ |
| REQ-101: User login workflow        | src/controllers/auth-controller.js, src/services/auth-service.js                                       |
| REQ-102: User registration          | src/controllers/signup-controller.js, src/services/user-service.js                                     |
| REQ-103: Password reset             | src/controllers/password-controller.js, src/services/email-service.js                                  |
| REQ-104: Data ingestion API         | src/controllers/data-controller.js, src/services/ingestion-service.js                                  |
| REQ-105: Reporting engine           | src/controllers/report-controller.js, src/services/report-service.js                                   |
| REQ-106: Email notification on signup | src/services/email-service.js                                                                          |
| REQ-107: Audit logging              | src/utils/logger.js                                                                                    |
| REQ-108: Admin dashboard UI         | **UNMAPPED**                                                                                           |
| REQ-109: Bulk data export           | **UNMAPPED**                                                                                           |