# ShelfOps Product Requirements Document (PRD)

## Product goal
ShelfOps helps D2C/FMCG teams recover lost quick-commerce sales caused by stockouts.

The product turns uploaded operations data into execution:
- detect stockout events,
- estimate commercial impact,
- diagnose likely causes,
- recommend replenishment actions,
- assign owners,
- track recovery status.

## Target users
- Sales operations managers at D2C/FMCG brands
- Modern trade / q-commerce key account managers
- Demand planning and supply chain coordinators
- Revenue operations / category analysts

## Initial customer segment
Small-to-mid-market D2C/FMCG brands selling on quick-commerce platforms in India and similar high-frequency markets, where stockout recovery speed strongly affects GMV.

## Core workflow
1. User uploads CSV/XLSX reports (SKU master + availability + inventory/supply files).
2. System validates and normalizes data.
3. System creates stockout recovery cases by SKU x location x platform x date.
4. System estimates lost revenue using sales velocity and stockout duration.
5. System runs rules-based root-cause diagnosis.
6. System recommends replenishment action and priority.
7. User assigns owner and due date.
8. User updates status until case is recovered or closed.

## MVP features
1. File upload + import history for required report types.
2. Validation report (accepted rows, rejected rows, error reasons).
3. Stockout case generation engine.
4. Lost revenue estimation model (transparent and editable assumptions).
5. Rules-based diagnosis engine using inventory, PO, dispatch, GRN signals.
6. Action recommendation templates with priority bands.
7. Case board/list with filters (status, platform, city, owner, impact).
8. Owner assignment and status transitions.
9. Recovery timeline tracking and basic analytics.

## Non-goals (MVP)
1. No digital shelf scraping/crawling.
2. No LLM or AI copilot in first version.
3. No advanced forecasting engine.
4. No deep ERP/native marketplace integrations.
5. No authentication/role management unless explicitly requested.
6. No mobile app in MVP.

## Success metrics
### Product metrics
- Time to first actionable case after upload: < 10 minutes
- % cases with diagnosis suggestion: > 90%
- % cases with recommended next action: > 95%

### Operational metrics
- Median time-to-assign case owner: < 1 business day
- Median time-to-recovery for high-priority stockouts: improved vs baseline

### Commercial metrics
- Estimated monthly revenue recovered (absolute)
- Recovery rate: recovered estimated lost revenue / total estimated lost revenue
- Stockout recurrence rate by SKU/location
