# Prototype State Matrix

| Scenario | Trigger | Address or action sequence | Visible state | Available actions | Recovery | Required |
| --- | --- | --- | --- | --- | --- | --- |
| Populated | Open feature | | Normal content | Primary actions | N/A | Yes |
| Loading | Start request | | Progress or skeleton | Cancel if supported | Success or error | As relevant |
| Empty | Successful empty response | | Guidance and next step | Create, clear, or retry | User action | As relevant |
| Error | Failed action | | Error with preserved context | Retry or dismiss | Return to prior state | Yes for networked flows |
| Long content | Stress fixture | | Wrapped or truncated content | Same as normal | N/A | As relevant |
| Permission | Restricted role | | Explanation and unavailable action | Request or navigate | Role change | As relevant |
| Offline | Connectivity loss | | Offline feedback | Retry | Reconnect | As relevant |

Delete irrelevant rows and add product-specific transitions. Keep fixtures deterministic.
