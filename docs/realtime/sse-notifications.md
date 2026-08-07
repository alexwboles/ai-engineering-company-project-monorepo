# RFP Ticket SSE Notifications

The RFP dashboard consumes `GET /rfp/tickets/stream` as an authenticated
Server-Sent Events stream. The stream is intentionally separate from the RFP
agent workflow: it carries ticket lifecycle metadata only and makes no model or
agent calls.

## Event contract

New tickets emit the named `rfp_ticket_created` event:

```text
id: 17
event: rfp_ticket_created
data: {"ticket_id":"...","status":"analyzing","created_at":"2026-08-07T12:00:00+00:00"}
```

Status changes emit `rfp_ticket_updated` with `ticket_id`, `status`, and
`updated_at`. Both event types are scoped to the authenticated ticket owner.
The broker keeps a bounded in-process replay window. The client sends its last
received event ID in `Last-Event-ID` after reconnecting, so missed events can be
replayed while already processed IDs are ignored by the client.

## Connection behavior

The dashboard uses `fetch` and a `ReadableStream` because the existing API uses
Bearer tokens in request headers. It reconnects after a dropped connection with
exponential backoff: 1, 2, 4, 8, 16, then 30 seconds. A keep-alive comment is
sent every 15 seconds when there is no event. The UI shows `connected` or
`reconnecting` and highlights a newly arrived RFP without reloading the ticket
list.

## Design decisions

- Each authenticated dashboard gets an independent subscription to the
  in-process broker. That is simple and keeps event delivery isolated between
  users. At approximately 50 concurrent users, the broker should move behind a
  shared Redis pub/sub or durable notification stream so multiple API workers
  share one event history rather than relying on process-local memory.
- A ticket created while a user is disconnected is recoverable while it remains
  in the bounded replay window. The `Last-Event-ID` cursor prevents duplicate
  delivery; if an outage exceeds the replay window, the dashboard's normal
  authenticated refresh remains the recovery path.
- SSE is the right fit because this feature is server-to-client notification
  with a simple reconnecting stream. WebSockets become preferable when the same
  connection must also carry interactive client commands, acknowledgements, or
  bidirectional agent token control; that is a separate communication contract.

## Manual verification

1. Sign in to the backoffice and open `/rfp` in two browser tabs.
2. In one tab, upload a valid HealthCore RFP PDF. Both tabs should show a cyan
   `New RFP ticket ... needs processing` notification without a page reload.
3. In DevTools, inspect the `GET /rfp/tickets/stream` response and confirm the
   named event and JSON payload above.
4. Disable the network for at least one tab, create another ticket from the
   connected tab, then restore the network. The disconnected tab should show
   `reconnecting`, reconnect, and display the missed ticket once. Its request
   includes `Last-Event-ID` and the ticket list must not contain duplicates.
