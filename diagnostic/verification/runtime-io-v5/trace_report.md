# Request boundary evidence

- go_running_ns is Go scheduler state time; OS descheduling or CPU quota throttling can occur within it.
- Connection pre-handler context includes idle, read-ahead and parsing; socket reads have no request byte framing.
- ConnState Active follows readRequest in Go 1.26.1, including parse errors; only a matched handler establishes a valid request.
- Socket Write return and connection Idle/Closed do not establish client receipt.
- Client and service absolute clocks are never subtracted.
- Reads spanning capture boundaries can be absent; read evidence is contextual, not an exhaustive packet timeline.

All outcomes: {"success": 2, "rejected": 1, "timeout": 1, "error": 0}

Clock mapping uncertainty (ns): 672

| Group / request | Interval | ms | Go Running ms | Runnable ms | Network wait ms | Other wait ms | Syscall ms | Other jobs completed |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| slow / 4 | handler | 0.0502 | 0.0250 | 0.0017 | 0.0000 | 0.0235 | 0.0000 | 0 |
| slow / 4 | handler_exit_to_connection_done | 0.0610 | 0.0215 | 0.0041 | 0.0000 | 0.0120 | 0.0235 | 0 |
| slow / 4 | connection_context_before_handler | 0.1174 | 0.0495 | 0.0006 | 0.0612 | 0.0000 | 0.0061 | 0 |
| slow / 4 | read_request_return_to_handler | 0.0192 | 0.0192 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| slow / 4 | handler_exit_to_first_socket_write | 0.0155 | 0.0155 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| slow / 4 | socket_write_0 | 0.0254 | 0.0019 | 0.0000 | 0.0000 | 0.0000 | 0.0235 | 0 |
| slow / 4 | final_socket_write_to_connection_done | 0.0201 | 0.0041 | 0.0041 | 0.0000 | 0.0120 | 0.0000 | 0 |
| slow / 4 | worker | 0.0157 | 0.0157 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| slow / 4 | worker_completion_to_handler_resume | 0.0065 | 0.0012 | 0.0017 | 0.0000 | 0.0035 | 0.0000 | 0 |
| slow / 4 | handler_resume_to_application_write | 0.0055 | 0.0055 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| slow / 4 | application_write | 0.0024 | 0.0024 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| slow / 4 | application_write_to_handler_exit | 0.0010 | 0.0010 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| typical / 4 | handler | 0.0502 | 0.0250 | 0.0017 | 0.0000 | 0.0235 | 0.0000 | 0 |
| typical / 4 | handler_exit_to_connection_done | 0.0610 | 0.0215 | 0.0041 | 0.0000 | 0.0120 | 0.0235 | 0 |
| typical / 4 | connection_context_before_handler | 0.1174 | 0.0495 | 0.0006 | 0.0612 | 0.0000 | 0.0061 | 0 |
| typical / 4 | read_request_return_to_handler | 0.0192 | 0.0192 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| typical / 4 | handler_exit_to_first_socket_write | 0.0155 | 0.0155 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| typical / 4 | socket_write_0 | 0.0254 | 0.0019 | 0.0000 | 0.0000 | 0.0000 | 0.0235 | 0 |
| typical / 4 | final_socket_write_to_connection_done | 0.0201 | 0.0041 | 0.0041 | 0.0000 | 0.0120 | 0.0000 | 0 |
| typical / 4 | worker | 0.0157 | 0.0157 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| typical / 4 | worker_completion_to_handler_resume | 0.0065 | 0.0012 | 0.0017 | 0.0000 | 0.0035 | 0.0000 | 0 |
| typical / 4 | handler_resume_to_application_write | 0.0055 | 0.0055 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| typical / 4 | application_write | 0.0024 | 0.0024 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| typical / 4 | application_write_to_handler_exit | 0.0010 | 0.0010 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |

Intervals overlap and must not be summed. JSON retains every outcome, syscall/other-wait time, read context and write errors.
No automatic mechanism or intervention is inferred. Inspect matched intervals and their association limits before proposing a controlled intervention.
